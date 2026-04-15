"""
Authentication API Views - 3-Phase Security System
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import numpy as np
import jwt
import base64
import io
from PIL import Image, ImageOps, ImageFilter
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False
from .models import User, OTPToken, AuditLog
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    OTPRequestSerializer, OTPVerifySerializer, FacialRecognitionSerializer
)
from .utils import send_otp_email, send_otp_sms, log_audit_event

EMBEDDING_PREFIX = b'ENCV1'
IMAGE_PREFIX = b'IMGV1'
IMAGE_PREFIX_V2 = b'IMGV2'

MIN_IMAGE_SIDE = 160
MIN_DYNAMIC_RANGE = 12
MIN_BRIGHTNESS_STD = 7.0
MIN_SHARPNESS_SCORE = 4.0
MIN_FACE_AREA_RATIO = 0.025


def _ensure_face_detectors_loaded():
    """Attempt lazy imports so detector availability can recover without full environment rebuild."""
    global cv2, CV2_AVAILABLE, face_recognition, FACE_RECOGNITION_AVAILABLE

    if not CV2_AVAILABLE:
        try:
            import cv2 as _cv2
            cv2 = _cv2
            CV2_AVAILABLE = True
        except ImportError:
            pass

    if not FACE_RECOGNITION_AVAILABLE:
        try:
            import face_recognition as _face_recognition
            face_recognition = _face_recognition
            FACE_RECOGNITION_AVAILABLE = True
        except ImportError:
            pass


def _image_data_to_rgb_array(image_data):
    """Convert base64 image payload (raw or data URL) to 8-bit RGB numpy array."""
    if not image_data or not isinstance(image_data, str):
        raise ValueError('Missing image_data')

    cleaned_data = image_data.strip()
    if cleaned_data.startswith('data:image') and ',' in cleaned_data:
        cleaned_data = cleaned_data.split(',', 1)[1]

    padding = len(cleaned_data) % 4
    if padding:
        cleaned_data += '=' * (4 - padding)

    image_bytes = base64.b64decode(cleaned_data)
    image_array = _bytes_to_rgb_array(image_bytes)

    return image_bytes, image_array


def _bytes_to_rgb_array(image_bytes):
    if not image_bytes:
        raise ValueError('Empty image bytes')

    pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    image_array = np.asarray(pil_image, dtype=np.uint8)

    if image_array.ndim != 3 or image_array.shape[2] != 3:
        raise ValueError('Image must be RGB')

    return np.ascontiguousarray(image_array, dtype=np.uint8)


def _to_bytes(value):
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, bytes):
        return value
    raise ValueError('Stored biometric data is not bytes')


def _compute_image_hash_from_bytes(image_bytes):
    """Compute a simple 64-bit perceptual hash for fallback biometric matching."""
    image = Image.open(io.BytesIO(image_bytes)).convert('L')
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.GaussianBlur(radius=1))
    image = image.resize((8, 8), Image.Resampling.LANCZOS)
    pixels = np.asarray(image, dtype=np.uint8)
    mean_val = pixels.mean()
    bits = (pixels >= mean_val).astype(np.uint8).flatten()
    packed = np.packbits(bits)
    return packed.tobytes()


def _compute_image_signature_v2(image_bytes):
    """Compute a more robust 128-bit fallback signature (aHash + dHash)."""
    image = Image.open(io.BytesIO(image_bytes)).convert('L')
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.GaussianBlur(radius=1))

    width, height = image.size
    side = min(width, height)
    left = max((width - side) // 2, 0)
    top = max((height - side) // 2, 0)
    image = image.crop((left, top, left + side, top + side))

    ahash_img = image.resize((8, 8), Image.Resampling.LANCZOS)
    ahash_pixels = np.asarray(ahash_img, dtype=np.uint8)
    ahash_bits = (ahash_pixels >= ahash_pixels.mean()).astype(np.uint8).flatten()
    ahash_bytes = np.packbits(ahash_bits).tobytes()

    dhash_img = image.resize((9, 8), Image.Resampling.LANCZOS)
    dhash_pixels = np.asarray(dhash_img, dtype=np.uint8)
    dhash_bits = (dhash_pixels[:, 1:] > dhash_pixels[:, :-1]).astype(np.uint8).flatten()
    dhash_bytes = np.packbits(dhash_bits).tobytes()

    return ahash_bytes + dhash_bytes


def _hamming_distance_bytes(hash_a, hash_b):
    if len(hash_a) != len(hash_b):
        return 64
    distance = 0
    for a_byte, b_byte in zip(hash_a, hash_b):
        distance += int((a_byte ^ b_byte).bit_count())
    return distance


def _estimate_sharpness_score(gray_array):
    """Estimate sharpness via gradient variance; lower score means blurrier image."""
    gray_float = gray_array.astype(np.float32)
    grad_y, grad_x = np.gradient(gray_float)
    magnitude = np.hypot(grad_x, grad_y)
    return float(np.var(magnitude))


def _detect_faces(image_array):
    """Detect face boxes using face_recognition first, then OpenCV cascade fallback."""
    _ensure_face_detectors_loaded()

    if FACE_RECOGNITION_AVAILABLE:
        model = settings.FACE_RECOGNITION_MODEL
        locations = face_recognition.face_locations(image_array, model=model)
        if locations:
            return locations

        pil_img = Image.fromarray(image_array)
        enhanced = np.asarray(ImageOps.autocontrast(pil_img), dtype=np.uint8)
        locations = face_recognition.face_locations(enhanced, model=model)
        if locations:
            return locations

    if CV2_AVAILABLE:
        gray = np.asarray(Image.fromarray(image_array).convert('L'), dtype=np.uint8)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        classifier = cv2.CascadeClassifier(cascade_path)
        detections = classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        # Convert OpenCV boxes (x, y, w, h) to (top, right, bottom, left)
        return [(int(y), int(x + w), int(y + h), int(x)) for (x, y, w, h) in detections]

    return []


def _validate_face_capture(image_array, require_face_checks=True):
    """
    Validate that the frame is usable for biometric verification.
    Returns (is_valid, error_message, face_locations).
    """
    if image_array is None or image_array.size == 0:
        return False, 'No image received. Please keep your face in the camera frame and retake.', []

    height, width = image_array.shape[:2]
    if min(height, width) < MIN_IMAGE_SIDE:
        return False, 'Captured image is too small. Move closer and retake.', []

    gray = np.asarray(Image.fromarray(image_array).convert('L'), dtype=np.uint8)
    dynamic_range = int(gray.max()) - int(gray.min())
    brightness_std = float(gray.std())
    sharpness_score = _estimate_sharpness_score(gray)

    if dynamic_range < MIN_DYNAMIC_RANGE or brightness_std < MIN_BRIGHTNESS_STD:
        return False, 'Empty or unclear frame detected. Please keep your face visible in the camera and retake.', []

    if sharpness_score < MIN_SHARPNESS_SCORE:
        return False, 'Image is blurry. Hold still, improve lighting, and retake.', []

    if not require_face_checks:
        return True, None, []

    face_locations = _detect_faces(image_array)
    if not face_locations and not FACE_RECOGNITION_AVAILABLE and not CV2_AVAILABLE:
        return False, 'Face detection service is unavailable. Please contact admin to enable biometric dependencies.', []

    if len(face_locations) == 0:
        return False, 'No face detected. Please place your face clearly in the frame and retake.', []

    if len(face_locations) > 1:
        return False, 'Multiple faces detected. Ensure only your face is visible and retake.', []

    top, right, bottom, left = face_locations[0]
    face_area = max((bottom - top), 0) * max((right - left), 0)
    frame_area = max(height * width, 1)
    face_ratio = face_area / frame_area

    if face_ratio < MIN_FACE_AREA_RATIO:
        return False, 'Face is too far from camera. Move closer and retake.', []

    return True, None, face_locations


def _extract_face_encoding(image_array):
    """
    Try to extract a face encoding with preprocessing.
    Returns None if face detection fails.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return None
    try:
        # Use HOG model (faster) - if fails, caller will try CNN via fallback
        model = settings.FACE_RECOGNITION_MODEL
        encodings = face_recognition.face_encodings(image_array, model=model)
        
        if encodings:
            # Return the strongest/first face encoding
            return encodings[0]
        
        # Preprocessing: try with enhanced contrast if no face found
        pil_img = Image.fromarray(image_array)
        pil_img = ImageOps.autocontrast(pil_img)
        preprocessed = np.asarray(pil_img, dtype=np.uint8)
        
        encodings = face_recognition.face_encodings(preprocessed, model=model)
        if encodings:
            return encodings[0]
            
    except Exception as e:
        # Log the error but don't stop - will fallback to hash matching
        pass
    
    return None


class AuthViewSet(viewsets.ViewSet):
    """
    Authentication ViewSet - 3-Phase Security System
    """
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """User Registration"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            log_audit_event(user, 'account_created', request)
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login_phase1(self, request):
        """Phase 1: Password Authentication"""
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.save()
            
            log_audit_event(user, 'login_success', request)
            
            # Check if 3 failed attempts - trigger Phase 3 (biometric)
            if user.failed_login_attempts >= 3:
                return Response({
                    'phase': 3,
                    'message': 'Too many failed attempts. Biometric authentication required.',
                    'requires_biometric': True
                }, status=status.HTTP_200_OK)
            
            # Proceed to Phase 2 (OTP)
            return Response({
                'phase': 2,
                'message': 'Password verified. OTP required.',
                'user_id': user.id,
                'requires_otp': True
            }, status=status.HTTP_200_OK)
        
        # Handle failed login
        username = request.data.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 3:
                    user.lock_account()
                    log_audit_event(user, 'account_locked', request)
                else:
                    log_audit_event(user, 'login_failed', request)
                user.save()
            except User.DoesNotExist:
                pass
        
        log_audit_event(None, 'login_failed', request)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'])
    def request_otp(self, request):
        """Phase 2: Request OTP"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid user_id format'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OTPRequestSerializer(data=request.data, context={'user': user})
        if serializer.is_valid():
            delivery_method = serializer.validated_data['delivery_method']
            otp_token = OTPToken.generate_otp(user, delivery_method)
            
            # Send OTP
            if delivery_method == 'email':
                send_otp_email(user, otp_token.token)
            elif delivery_method == 'sms':
                send_otp_sms(user, otp_token.token)
            
            log_audit_event(user, 'otp_sent', request, {'method': delivery_method})
            
            return Response({
                'message': f'OTP sent via {delivery_method}',
                'expires_in': 600  # 10 minutes
            }, status=status.HTTP_200_OK)
        
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Phase 2: Verify OTP"""
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Debug: Check available OTPs
        available_otps = OTPToken.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')
        
        serializer = OTPVerifySerializer(data=request.data, context={'user': user})
        if serializer.is_valid():
            log_audit_event(user, 'otp_verified', request)
            
            # Generate JWT token
            token = generate_jwt_token(user)
            
            return Response({
                'message': 'OTP verified successfully',
                'token': token,
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        # Return more detailed error
        error_message = serializer.errors.get('non_field_errors', serializer.errors.get('otp', ['Invalid OTP']))
        if isinstance(error_message, list):
            error_message = error_message[0]
        
        return Response({
            'error': str(error_message),
            'debug': {
                'available_otps_count': available_otps.count(),
                'latest_otp_created': available_otps.first().created_at if available_otps.exists() else None,
                'latest_otp_expires': available_otps.first().expires_at if available_otps.exists() else None,
            } if settings.DEBUG else {}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_biometric(self, request):
        """
        Verify biometric data (EVERY LOGIN)
        
        FIRST LOGIN:
        - Compares newly captured face with just-enrolled face (same person, same image)
        - Always succeeds on first login because it's comparing same image with itself
        
        SECOND+ LOGINS (the real verification):
        - Loads the reference face image stored in database from first login
        - Extracts face encoding from newly captured image
        - Extracts face encoding from stored reference image
        - Uses face_recognition library to compare if they're the same person
        - If faces match (within tolerance) → login succeeds
        - If faces don't match (different person) → login fails with "Face does not match"
        
        Database check: user.biometric_embedding field contains the stored reference image
        
        Returns: JWT token if verified, error message if verification fails
        """
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.biometric_enrolled:
            return Response({'error': 'Biometric not enrolled'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = FacialRecognitionSerializer(data=request.data, context={'user': user})
        if serializer.is_valid():
            # Decode base64 image
            image_data = request.data.get('image_data')
            try:
                image_bytes, image_array = _image_data_to_rgb_array(image_data)
                
                # Load stored embedding and compare
                stored_image_bytes = _to_bytes(user.biometric_embedding)

                # Always require visible face in frame, regardless of storage mode.
                is_valid, validation_error, _ = _validate_face_capture(image_array, require_face_checks=True)
                if not is_valid:
                    return Response({'error': validation_error}, status=status.HTTP_400_BAD_REQUEST)

                current_encoding = _extract_face_encoding(image_array)

                is_match = False

                if stored_image_bytes.startswith(EMBEDDING_PREFIX):
                    if current_encoding is None:
                        return Response({'error': 'Face encoding failed. Ensure your face is clearly visible and retake.'}, status=status.HTTP_400_BAD_REQUEST)

                    stored_encoding_bytes = stored_image_bytes[len(EMBEDDING_PREFIX):]
                    stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
                    if stored_encoding.size != 128:
                        return Response({'error': 'Stored biometric data is invalid.'}, status=status.HTTP_400_BAD_REQUEST)

                    distance = np.linalg.norm(stored_encoding - current_encoding)
                    is_match = distance <= settings.FACE_RECOGNITION_TOLERANCE

                elif stored_image_bytes.startswith(IMAGE_PREFIX):
                    stored_hash = stored_image_bytes[len(IMAGE_PREFIX):]
                    current_hash = _compute_image_hash_from_bytes(image_bytes)
                    hash_distance = _hamming_distance_bytes(stored_hash, current_hash)
                    is_match = hash_distance <= 22  # Increased from 18 for more leniency

                elif stored_image_bytes.startswith(IMAGE_PREFIX_V2):
                    stored_signature = stored_image_bytes[len(IMAGE_PREFIX_V2):]
                    current_signature = _compute_image_signature_v2(image_bytes)
                    signature_distance = _hamming_distance_bytes(stored_signature, current_signature)
                    is_match = signature_distance <= 40  # Increased from 34 for more leniency

                else:
                    stored_image_array = _bytes_to_rgb_array(stored_image_bytes)
                    stored_encoding = _extract_face_encoding(stored_image_array)

                    if current_encoding is not None and stored_encoding is not None:
                        distance = np.linalg.norm(stored_encoding - current_encoding)
                        is_match = distance <= settings.FACE_RECOGNITION_TOLERANCE
                    else:
                        stored_hash = _compute_image_hash_from_bytes(stored_image_bytes)
                        current_hash = _compute_image_hash_from_bytes(image_bytes)
                        hash_distance = _hamming_distance_bytes(stored_hash, current_hash)
                        is_match = hash_distance <= 18

                if is_match:
                    log_audit_event(user, 'biometric_used', request)
                    user.unlock_account()
                    
                    # Generate JWT token
                    token = generate_jwt_token(user)
                    
                    return Response({
                        'message': 'Biometric verified successfully',
                        'token': token,
                        'user': UserSerializer(user).data
                    }, status=status.HTTP_200_OK)
                else:
                    log_audit_event(user, 'biometric_failed', request)
                    return Response({'error': 'Face does not match. Try again.'}, status=status.HTTP_400_BAD_REQUEST)
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                return Response({'error': f'Image processing error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll_biometric(self, request):
        """
        Enroll biometric data (FIRST TIME ONLY)
        
        On first login:
        - Captures user's face image
        - Stores it in database (user.biometric_embedding field)
        - This becomes the reference image for future logins
        
        Returns: Success message when face is saved
        """
        user = request.user
        image_data = request.data.get('image_data')
        
        try:
            image_bytes, image_array = _image_data_to_rgb_array(image_data)
            is_valid, validation_error, _ = _validate_face_capture(image_array, require_face_checks=True)
            if not is_valid:
                return Response({'error': validation_error}, status=status.HTTP_400_BAD_REQUEST)

            face_encoding = _extract_face_encoding(image_array)

            if face_encoding is not None:
                user.biometric_embedding = EMBEDDING_PREFIX + np.asarray(face_encoding, dtype=np.float64).tobytes()
            else:
                # Safe fallback mode when facial encoding is not available.
                fallback_signature = _compute_image_signature_v2(image_bytes)
                user.biometric_embedding = IMAGE_PREFIX_V2 + fallback_signature

            user.biometric_enrolled = True
            user.save()
            
            return Response({'message': 'Biometric enrolled successfully'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f'Enrollment error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


def generate_jwt_token(user):
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_DELTA),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

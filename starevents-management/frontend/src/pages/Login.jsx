import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../api/axios'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Loading from '../components/ui/Loading'
import Webcam from 'react-webcam'
import { Lock, Mail, Smartphone, Shield } from 'lucide-react'

const Login = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [phase, setPhase] = useState(1) // 1: password, 2: OTP, 3: biometric
  const [userId, setUserId] = useState(null)
  const [deliveryMethod, setDeliveryMethod] = useState('email')
  const [capturedImage, setCapturedImage] = useState(null)
  const [otpAuthData, setOtpAuthData] = useState(null)
  const [biometricLoading, setBiometricLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const webcamRef = useRef(null)
  
  const { login } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      const response = await api.post('/auth/login_phase1/', { username, password })
      const { phase: nextPhase, user_id, requires_otp, requires_biometric } = response.data
      
      if (requires_biometric) {
        setPhase(3)
        setUserId(user_id)
        showToast('Too many failed attempts. Biometric authentication required.', 'warning')
      } else if (requires_otp) {
        setPhase(2)
        setUserId(user_id)
        // Call requestOTP with user_id directly to avoid timing issues
        await requestOTP(user_id)
        showToast('OTP sent successfully', 'success')
      }
    } catch (err) {
      showToast(err.response?.data?.error || 'Invalid credentials', 'error')
    } finally {
      setLoading(false)
    }
  }

  const requestOTP = async (userIdParam = null) => {
    try {
      const userIdToUse = userIdParam || userId
      if (!userIdToUse) {
        showToast('User ID is missing', 'error')
        return
      }
      await api.post('/auth/request_otp/', {
        user_id: userIdToUse,
        delivery_method: deliveryMethod
      })
    } catch (err) {
      console.error('OTP request error:', err.response?.data)
      const errorData = err.response?.data
      let errorMessage = 'Failed to send OTP'
      
      if (errorData) {
        if (errorData.error) {
          errorMessage = errorData.error
        } else if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors) 
            ? errorData.non_field_errors[0] 
            : errorData.non_field_errors
        }
      }
      
      showToast(errorMessage, 'error')
    }
  }

  const handleOTPVerify = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      const response = await api.post('/auth/verify_otp/', {
        user_id: userId,
        otp: otp
      })

      setOtpAuthData({
        user: response.data.user,
        token: response.data.token
      })
      setCapturedImage(null)
      setPhase(3)
      showToast('OTP verified. Continue with face detection.', 'success')
    } catch (err) {
      showToast(err.response?.data?.error || 'Invalid OTP', 'error')
    } finally {
      setLoading(false)
    }
  }

  const captureImage = () => {
    const video = webcamRef.current?.video
    if (!video || video.readyState !== 4) {
      showToast('Camera is not ready. Please allow camera access and try again.', 'error')
      return
    }

    const frameCanvas = document.createElement('canvas')
    frameCanvas.width = video.videoWidth || 720
    frameCanvas.height = video.videoHeight || 480
    const frameCtx = frameCanvas.getContext('2d')
    if (!frameCtx) {
      showToast('Unable to process camera frame. Please try again.', 'error')
      return
    }

    frameCtx.drawImage(video, 0, 0, frameCanvas.width, frameCanvas.height)
    const frame = frameCtx.getImageData(0, 0, frameCanvas.width, frameCanvas.height).data
    let total = 0
    let totalSq = 0
    const sampleStep = 32

    for (let i = 0; i < frame.length; i += sampleStep) {
      const r = frame[i]
      const g = frame[i + 1]
      const b = frame[i + 2]
      const brightness = 0.299 * r + 0.587 * g + 0.114 * b
      total += brightness
      totalSq += brightness * brightness
    }

    const count = Math.max(frame.length / sampleStep, 1)
    const mean = total / count
    const variance = Math.max(totalSq / count - mean * mean, 0)
    const stdDev = Math.sqrt(variance)

    if (mean < 15 || stdDev < 8) {
      showToast('No clear face in camera. Keep your face in frame and try capture again.', 'warning')
      return
    }

    const imageSrc = webcamRef.current?.getScreenshot()
    if (!imageSrc) {
      showToast('Unable to capture image. Please allow camera access.', 'error')
      return
    }
    setCapturedImage(imageSrc)
  }

  const getImagePayload = (imageData) => {
    if (!imageData) return ''
    return imageData.includes(',') ? imageData.split(',')[1] : imageData
  }

  const completeBiometricAuth = async () => {
    if (!capturedImage) {
      showToast('Please capture your face first.', 'warning')
      return
    }

    const imagePayload = getImagePayload(capturedImage)

    setBiometricLoading(true)
    try {
      // Only enroll if explicitly marked not enrolled by backend
      if (otpAuthData?.user?.biometric_enrolled === false) {
        showToast('Enrolling your face for first time...', 'info')
        await api.post(
          '/auth/enroll_biometric/',
          { image_data: imagePayload },
          {
            headers: {
              Authorization: `Bearer ${otpAuthData.token}`
            }
          }
        )
        showToast('Face enrolled successfully!', 'success')
      }

      // Verify the face (on first login compares with just-enrolled image, on subsequent logins compares with stored enrollment)
      const verifyResponse = await api.post('/auth/verify_biometric/', {
        user_id: userId,
        image_data: imagePayload
      })

      login(verifyResponse.data.user, verifyResponse.data.token)
      showToast('Face verified. Login successful!', 'success')
      navigate('/dashboard')
    } catch (err) {
      const errorMessage = err.response?.data?.error || 'Face verification failed'

      // Recovery path: OTP is already verified, so we can refresh stored biometric data
      // for this authenticated session and retry verification once.
      if (
        errorMessage.toLowerCase().includes('face does not match') &&
        otpAuthData?.token
      ) {
        try {
          showToast('Updating your biometric profile. Please wait...', 'info')
          await api.post(
            '/auth/enroll_biometric/',
            { image_data: imagePayload },
            {
              headers: {
                Authorization: `Bearer ${otpAuthData.token}`
              }
            }
          )

          const retryVerifyResponse = await api.post('/auth/verify_biometric/', {
            user_id: userId,
            image_data: imagePayload
          })

          login(retryVerifyResponse.data.user, retryVerifyResponse.data.token)
          showToast('Biometric updated and verified. Login successful!', 'success')
          navigate('/dashboard')
          return
        } catch (retryErr) {
          showToast(retryErr.response?.data?.error || errorMessage, 'error')
        }
      } else {
        showToast(errorMessage, 'error')
      }

      setCapturedImage(null)
    } finally {
      setBiometricLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="mx-auto h-16 w-16 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
            <span className="text-white font-bold text-2xl">SE</span>
          </div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            StarEvents Management
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {phase === 1 && 'Sign in to your account'}
            {phase === 2 && 'Enter your OTP code'}
            {phase === 3 && 'Biometric authentication required'}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          {phase === 1 && (
            <form onSubmit={handlePasswordLogin} className="space-y-6">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    required
                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Shield className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    required
                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="w-full"
                size="lg"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Signing in...
                  </span>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>
          )}

          {phase === 2 && (
            <form onSubmit={handleOTPVerify} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  OTP Delivery Method
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => { 
                      setDeliveryMethod('email')
                      requestOTP(userId)
                    }}
                    className={`p-3 border-2 rounded-lg transition-all ${
                      deliveryMethod === 'email'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Mail className="w-5 h-5 mx-auto mb-1" />
                    <span className="text-sm font-medium">Email</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => { 
                      setDeliveryMethod('sms')
                      requestOTP(userId)
                    }}
                    className={`p-3 border-2 rounded-lg transition-all ${
                      deliveryMethod === 'sms'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Smartphone className="w-5 h-5 mx-auto mb-1" />
                    <span className="text-sm font-medium">SMS</span>
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => requestOTP(userId)}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Resend OTP
                </button>
              </div>
              <div>
                <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2">
                  Enter 6-digit OTP
                </label>
                <input
                  id="otp"
                  name="otp"
                  type="text"
                  maxLength="6"
                  required
                  className="block w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center text-2xl font-mono tracking-widest"
                  placeholder="000000"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                />
              </div>
              <Button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full"
                size="lg"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Verifying...
                  </span>
                ) : (
                  'Verify OTP'
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setPhase(1)}
                className="w-full"
              >
                Back to Login
              </Button>
            </form>
          )}

          {phase === 3 && (
            <div className="space-y-6">
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  Complete face detection to finish login.
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                {capturedImage ? (
                  <img
                    src={capturedImage}
                    alt="Captured face"
                    className="w-full rounded-lg"
                  />
                ) : (
                  <Webcam
                    ref={webcamRef}
                    audio={false}
                    screenshotFormat="image/jpeg"
                    className="w-full rounded-lg"
                    videoConstraints={{
                      width: 720,
                      height: 480,
                      facingMode: 'user'
                    }}
                  />
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  onClick={captureImage}
                  disabled={biometricLoading || !!capturedImage}
                >
                  Capture
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCapturedImage(null)}
                  disabled={biometricLoading || !capturedImage}
                >
                  Retake
                </Button>
              </div>

              <Button
                type="button"
                className="w-full"
                onClick={completeBiometricAuth}
                disabled={biometricLoading || !capturedImage}
              >
                {biometricLoading ? 'Verifying face...' : 'Verify Face & Continue'}
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setPhase(1)
                  setOtp('')
                  setCapturedImage(null)
                  setOtpAuthData(null)
                }}
                className="w-full"
                disabled={biometricLoading}
              >
                Back to Login
              </Button>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-gray-600">
          Secure 3-phase authentication system
        </p>
      </div>
    </div>
  )
}

export default Login

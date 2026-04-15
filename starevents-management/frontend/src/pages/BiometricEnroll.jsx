import { useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import Button from '../components/ui/Button'
import { Shield } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'

const BiometricEnroll = () => {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const { showToast } = useToast()
  const navigate = useNavigate()

  const startCamera = async () => {
    if (cameraActive) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setCameraActive(true)
      }
    } catch (error) {
      console.error('Camera error:', error)
      showToast('Unable to access camera. Please check permissions.', 'error')
    }
  }

  const stopCamera = () => {
    const video = videoRef.current
    if (video && video.srcObject) {
      const tracks = video.srcObject.getTracks()
      tracks.forEach((t) => t.stop())
      video.srcObject = null
    }
    setCameraActive(false)
  }

  useEffect(() => {
    return () => {
      stopCamera()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleEnroll = async () => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas) {
      showToast('Camera not ready. Please start camera first.', 'error')
      return
    }

    const width = video.videoWidth
    const height = video.videoHeight

    if (!width || !height) {
      showToast('Camera not ready. Please wait a moment and try again.', 'error')
      return
    }

    try {
      setLoading(true)

      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        showToast('Unable to process camera frame. Please try again.', 'error')
        return
      }

      ctx.drawImage(video, 0, 0, width, height)

      const frame = ctx.getImageData(0, 0, width, height).data
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
        showToast('No clear face in camera. Keep your face visible and try again.', 'warning')
        return
      }

      const dataUrl = canvas.toDataURL('image/png')
      const base64Image = dataUrl.split(',')[1]

      await api.post('/auth/enroll_biometric/', {
        image_data: base64Image,
      })

      showToast('Biometric enrolled successfully.', 'success')
      stopCamera()
      navigate('/dashboard')
    } catch (error) {
      console.error('Enroll biometric error:', error.response?.data || error)
      const message =
        error.response?.data?.error ||
        error.response?.data?.message ||
        'Failed to enroll biometric.'
      showToast(message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div className="flex items-center space-x-3">
        <Shield className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Enroll Biometric Login</h1>
          <p className="text-sm text-gray-500">
            Capture your face once to enable face recognition during secure login.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-64 h-48 bg-black rounded-lg overflow-hidden flex items-center justify-center">
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              autoPlay
              playsInline
            />
          </div>
          <canvas ref={canvasRef} className="hidden" />
          <p className="text-xs text-gray-500 text-center">
            Make sure your face is clearly visible, in good lighting, and centered in the frame.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={startCamera}
          >
            {cameraActive ? 'Restart Camera' : 'Start Camera'}
          </Button>
          <Button
            type="button"
            className="w-full"
            onClick={handleEnroll}
            disabled={!cameraActive || loading}
          >
            {loading ? 'Enrolling...' : 'Enroll Face'}
          </Button>
        </div>

        <Button
          type="button"
          variant="outline"
          className="w-full mt-2"
          onClick={() => {
            stopCamera()
            navigate('/dashboard')
          }}
        >
          Back to Dashboard
        </Button>
      </div>
    </div>
  )
}

export default BiometricEnroll


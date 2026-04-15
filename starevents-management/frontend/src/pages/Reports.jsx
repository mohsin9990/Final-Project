import { useState } from 'react'
import api from '../api/axios'
import { useToast } from '../contexts/ToastContext'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import Input from '../components/ui/Input'
import Loading from '../components/ui/Loading'
import { FileText, Download, Calendar, Package, TrendingUp } from 'lucide-react'

const Reports = () => {
  const [loading, setLoading] = useState(false)
  const [reportType, setReportType] = useState('inventory_status')
  const [format, setFormat] = useState('pdf')
  const [category, setCategory] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [eventId, setEventId] = useState('')
  const [generatedReports, setGeneratedReports] = useState([])
  const { showToast } = useToast()

  const generateReport = async () => {
    try {
      setLoading(true)
      let response

      switch (reportType) {
        case 'inventory_status':
          response = await api.post('/reports/generate_inventory_status/', {
            format,
            category: category || undefined
          })
          break
        case 'stock_summary':
          response = await api.post('/reports/generate_stock_summary/', {
            format,
            start_date: startDate || undefined,
            end_date: endDate || undefined
          })
          break
        case 'event_resources':
          response = await api.post('/reports/generate_event_resources/', {
            format,
            event_id: eventId || undefined
          })
          break
        default:
          throw new Error('Invalid report type')
      }

      showToast('Report generated successfully', 'success')
      setGeneratedReports(prev => [response.data.report, ...prev])
    } catch (error) {
      showToast(error.response?.data?.error || 'Failed to generate report', 'error')
    } finally {
      setLoading(false)
    }
  }

  const downloadReport = async (reportId) => {
    try {
      const response = await api.get(`/reports/${reportId}/download/`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `report_${reportId}.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      showToast('Report downloaded successfully', 'success')
    } catch (error) {
      showToast('Failed to download report', 'error')
    }
  }

  const reportTypes = [
    {
      value: 'inventory_status',
      label: 'Inventory Status Report',
      icon: Package,
      description: 'Current inventory levels and stock status',
      fields: ['category']
    },
    {
      value: 'stock_summary',
      label: 'Stock Summary Report',
      icon: TrendingUp,
      description: 'Stock transactions and movements',
      fields: ['start_date', 'end_date']
    },
    {
      value: 'event_resources',
      label: 'Event Resources Report',
      icon: Calendar,
      description: 'Resources allocated to events',
      fields: ['event_id']
    }
  ]

  const selectedReportType = reportTypes.find(rt => rt.value === reportType)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-500">Generate and download reports in PDF or Excel format</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generator */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-xl font-semibold text-gray-900">Generate Report</h2>
            </CardHeader>
            <CardBody className="space-y-4">
              <Select
                label="Report Type"
                value={reportType}
                onChange={(e) => {
                  setReportType(e.target.value)
                  setCategory('')
                  setStartDate('')
                  setEndDate('')
                  setEventId('')
                }}
              >
                {reportTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </Select>

              {selectedReportType && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-start">
                    {selectedReportType.icon && (
                      <selectedReportType.icon className="w-5 h-5 text-blue-600 mt-0.5 mr-3" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-blue-900">{selectedReportType.label}</p>
                      <p className="text-sm text-blue-700 mt-1">{selectedReportType.description}</p>
                    </div>
                  </div>
                </div>
              )}

              <Select
                label="Format"
                value={format}
                onChange={(e) => setFormat(e.target.value)}
              >
                <option value="pdf">PDF</option>
                <option value="excel">Excel</option>
              </Select>

              {/* Dynamic Fields */}
              {selectedReportType?.fields.includes('category') && (
                <Select
                  label="Category (Optional)"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="">All Categories</option>
                  <option value="equipment">Equipment</option>
                  <option value="consumable">Consumable</option>
                  <option value="furniture">Furniture</option>
                  <option value="decor">Decor</option>
                  <option value="audio_visual">Audio Visual</option>
                  <option value="catering">Catering</option>
                </Select>
              )}

              {selectedReportType?.fields.includes('start_date') && (
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Start Date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                  <Input
                    label="End Date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              )}

              {selectedReportType?.fields.includes('event_id') && (
                <Input
                  label="Event ID (Optional)"
                  type="number"
                  value={eventId}
                  onChange={(e) => setEventId(e.target.value)}
                  placeholder="Leave empty for all events"
                />
              )}

              <Button
                onClick={generateReport}
                disabled={loading}
                className="w-full"
                size="lg"
              >
                {loading ? (
                  <span className="flex items-center">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Generating...
                  </span>
                ) : (
                  <>
                    <FileText className="w-5 h-5 mr-2" />
                    Generate Report
                  </>
                )}
              </Button>
            </CardBody>
          </Card>

          {/* Generated Reports */}
          {generatedReports.length > 0 && (
            <Card>
              <CardHeader>
                <h2 className="text-xl font-semibold text-gray-900">Recently Generated</h2>
              </CardHeader>
              <CardBody>
                <div className="space-y-3">
                  {generatedReports.map((report) => (
                    <div
                      key={report.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{report.title}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(report.generated_at).toLocaleString()} • {report.format.toUpperCase()}
                          </p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadReport(report.id)}
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Download
                      </Button>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}
        </div>

        {/* Info Card */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Report Types</h3>
          </CardHeader>
          <CardBody className="space-y-4">
            {reportTypes.map((type) => {
              const Icon = type.icon
              return (
                <div
                  key={type.value}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    reportType === type.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start">
                    <Icon className="w-5 h-5 text-gray-600 mt-0.5 mr-3" />
                    <div>
                      <p className="font-medium text-gray-900">{type.label}</p>
                      <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

export default Reports

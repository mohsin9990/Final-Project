import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import api from '../api/axios'
import { useToast } from '../contexts/ToastContext'
import Card, { CardBody, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import Loading from '../components/ui/Loading'
import { Plus, Search, Edit, Trash2, Eye, Calendar, MapPin, Users, DollarSign } from 'lucide-react'

const Events = () => {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const { showToast } = useToast()
  const { register, handleSubmit, reset, formState: { errors } } = useForm()

  useEffect(() => {
    fetchEvents()
  }, [filterCategory, filterStatus])

  const fetchEvents = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (filterCategory) params.append('category', filterCategory)
      if (filterStatus) params.append('status', filterStatus)
      
      const response = await api.get(`/events/events/?${params}`)
      setEvents(response.data.results || response.data || [])
    } catch (error) {
      showToast('Failed to fetch events', 'error')
    } finally {
      setLoading(false)
    }
  }

  const onSubmit = async (data) => {
    try {
      if (selectedEvent) {
        await api.put(`/events/events/${selectedEvent.id}/`, data)
        showToast('Event updated successfully', 'success')
      } else {
        await api.post('/events/events/', data)
        showToast('Event created successfully', 'success')
      }
      setIsModalOpen(false)
      reset()
      setSelectedEvent(null)
      fetchEvents()
    } catch (error) {
      showToast(error.response?.data?.error || 'Failed to save event', 'error')
    }
  }

  const handleEdit = (event) => {
    setSelectedEvent(event)
    reset({
      title: event.title,
      description: event.description,
      category: event.category,
      venue: event.venue,
      start_date: event.start_date?.slice(0, 16),
      end_date: event.end_date?.slice(0, 16),
      capacity: event.capacity,
      price: event.price,
      status: event.status
    })
    setIsModalOpen(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this event?')) return
    
    try {
      await api.delete(`/events/events/${id}/`)
      showToast('Event deleted successfully', 'success')
      fetchEvents()
    } catch (error) {
      showToast('Failed to delete event', 'error')
    }
  }

  const handlePublish = async (id) => {
    try {
      await api.post(`/events/events/${id}/publish/`)
      showToast('Event published successfully', 'success')
      fetchEvents()
    } catch (error) {
      showToast('Failed to publish event', 'error')
    }
  }

  const filteredEvents = events.filter(event => {
    const matchesSearch = event.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         event.description?.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  const getStatusColor = (status) => {
    const colors = {
      draft: 'bg-gray-100 text-gray-800',
      published: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      completed: 'bg-blue-100 text-blue-800'
    }
    return colors[status] || colors.draft
  }

  const getCategoryColor = (category) => {
    const colors = {
      corporate: 'bg-blue-100 text-blue-800',
      wedding: 'bg-pink-100 text-pink-800',
      birthday: 'bg-yellow-100 text-yellow-800',
      conference: 'bg-purple-100 text-purple-800',
      seminar: 'bg-indigo-100 text-indigo-800',
      other: 'bg-gray-100 text-gray-800'
    }
    return colors[category] || colors.other
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Events</h1>
          <p className="mt-1 text-sm text-gray-500">Manage your events and bookings</p>
        </div>
        <Button onClick={() => { setSelectedEvent(null); reset(); setIsModalOpen(true) }}>
          <Plus className="w-4 h-4 mr-2" />
          Create Event
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search events..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <Select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              <option value="corporate">Corporate</option>
              <option value="wedding">Wedding</option>
              <option value="birthday">Birthday</option>
              <option value="conference">Conference</option>
              <option value="seminar">Seminar</option>
              <option value="other">Other</option>
            </Select>
            <Select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">All Status</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="cancelled">Cancelled</option>
              <option value="completed">Completed</option>
            </Select>
            <Button variant="outline" onClick={() => { setSearchTerm(''); setFilterCategory(''); setFilterStatus('') }}>
              Clear Filters
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Events Grid */}
      {loading ? (
        <Loading className="py-12" />
      ) : filteredEvents.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No events found</p>
          </CardBody>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredEvents.map((event) => (
            <Card key={event.id} hover>
              {event.image && (
                <img src={event.image} alt={event.title} className="w-full h-48 object-cover rounded-t-xl" />
              )}
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{event.title}</h3>
                    <div className="flex flex-wrap gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getCategoryColor(event.category)}`}>
                        {event.category}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(event.status)}`}>
                        {event.status}
                      </span>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardBody>
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">{event.description}</p>
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center">
                    <MapPin className="w-4 h-4 mr-2" />
                    {event.venue}
                  </div>
                  <div className="flex items-center">
                    <Calendar className="w-4 h-4 mr-2" />
                    {new Date(event.start_date).toLocaleDateString()}
                  </div>
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-2" />
                    {event.available_capacity || event.capacity} / {event.capacity} available
                  </div>
                  <div className="flex items-center">
                    <DollarSign className="w-4 h-4 mr-2" />
                    £{event.price}
                  </div>
                </div>
              </CardBody>
              <div className="px-6 py-4 border-t border-gray-200 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => handleEdit(event)}>
                  <Edit className="w-4 h-4 mr-1" />
                  Edit
                </Button>
                {event.status === 'draft' && (
                  <Button size="sm" variant="success" onClick={() => handlePublish(event.id)}>
                    Publish
                  </Button>
                )}
                <Button size="sm" variant="danger" onClick={() => handleDelete(event.id)}>
                  <Trash2 className="w-4 h-4 mr-1" />
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); reset(); setSelectedEvent(null) }}
        title={selectedEvent ? 'Edit Event' : 'Create New Event'}
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Event Title"
            {...register('title', { required: 'Title is required' })}
            error={errors.title?.message}
          />
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              {...register('description', { required: 'Description is required' })}
              rows={4}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 ${
                errors.description ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category"
              {...register('category', { required: 'Category is required' })}
              error={errors.category?.message}
            >
              <option value="">Select category</option>
              <option value="corporate">Corporate</option>
              <option value="wedding">Wedding</option>
              <option value="birthday">Birthday</option>
              <option value="conference">Conference</option>
              <option value="seminar">Seminar</option>
              <option value="other">Other</option>
            </Select>

            <Select
              label="Status"
              {...register('status')}
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="cancelled">Cancelled</option>
            </Select>
          </div>

          <Input
            label="Venue"
            {...register('venue', { required: 'Venue is required' })}
            error={errors.venue?.message}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date & Time"
              type="datetime-local"
              {...register('start_date', { required: 'Start date is required' })}
              error={errors.start_date?.message}
            />
            <Input
              label="End Date & Time"
              type="datetime-local"
              {...register('end_date', { required: 'End date is required' })}
              error={errors.end_date?.message}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Capacity"
              type="number"
              {...register('capacity', { required: 'Capacity is required', min: 1 })}
              error={errors.capacity?.message}
            />
            <Input
              label="Price (£)"
              type="number"
              step="0.01"
              {...register('price', { required: 'Price is required', min: 0 })}
              error={errors.price?.message}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => { setIsModalOpen(false); reset() }}>
              Cancel
            </Button>
            <Button type="submit">
              {selectedEvent ? 'Update Event' : 'Create Event'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default Events

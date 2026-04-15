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
import { Plus, Search, Edit, Trash2, AlertTriangle, Package, TrendingUp, TrendingDown } from 'lucide-react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const Inventory = () => {
  const [items, setItems] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isTransactionModalOpen, setIsTransactionModalOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(null)
  const [selectedItemForTransaction, setSelectedItemForTransaction] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [showLowStock, setShowLowStock] = useState(false)
  const { showToast } = useToast()
  
  // Separate form instances for item form and transaction form
  const itemForm = useForm({
    mode: 'onSubmit',
    reValidateMode: 'onChange'
  })
  
  const transactionForm = useForm({
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: {
      type: 'in',
      quantity: '',
      notes: ''
    }
  })
  
  const onItemFormError = (errors) => {
    console.log('Item form validation errors:', errors)
    const firstError = Object.values(errors)[0]
    if (firstError?.message) {
      showToast(firstError.message, 'error')
    }
  }
  
  const onTransactionFormError = (errors) => {
    console.log('Transaction form validation errors:', errors)
    const firstError = Object.values(errors)[0]
    if (firstError?.message) {
      showToast(firstError.message, 'error')
    }
  }

  useEffect(() => {
    fetchInventory()
    fetchTransactions()
  }, [filterCategory, showLowStock])

  const fetchInventory = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (filterCategory) params.append('category', filterCategory)
      if (showLowStock) params.append('low_stock', 'true')
      
      const response = await api.get(`/inventory/items/?${params}`)
      setItems(response.data.results || response.data || [])
    } catch (error) {
      showToast('Failed to fetch inventory', 'error')
    } finally {
      setLoading(false)
    }
  }

  const fetchTransactions = async () => {
    try {
      const response = await api.get('/inventory/transactions/')
      setTransactions(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error fetching transactions:', error)
    }
  }

  const onSubmit = async (data) => {
    try {
      // Convert number fields to proper types and handle empty strings
      const itemData = {
        name: data.name?.trim(),
        description: data.description?.trim() || '',
        sku: data.sku?.trim(),
        category: data.category,
        unit: data.unit,
        current_stock: data.current_stock ? parseFloat(data.current_stock) : 0,
        minimum_stock: data.minimum_stock ? parseFloat(data.minimum_stock) : 0,
        maximum_stock: data.maximum_stock && data.maximum_stock !== '' ? parseFloat(data.maximum_stock) : null,
        unit_price: data.unit_price ? parseFloat(data.unit_price) : 0,
        supplier: data.supplier?.trim() || '',
        location: data.location?.trim() || '',
      }
      
      console.log('Submitting item data:', itemData)
      
      if (selectedItem) {
        await api.put(`/inventory/items/${selectedItem.id}/`, itemData)
        showToast('Item updated successfully', 'success')
      } else {
        await api.post('/inventory/items/', itemData)
        showToast('Item created successfully', 'success')
      }
      setIsModalOpen(false)
      itemForm.reset()
      setSelectedItem(null)
      fetchInventory()
    } catch (error) {
      console.error('Item save error:', error)
      console.error('Error response:', error.response?.data)
      
      let errorMessage = 'Failed to save item'
      if (error.response?.data) {
        if (typeof error.response.data === 'string') {
          errorMessage = error.response.data
        } else if (error.response.data.error) {
          errorMessage = error.response.data.error
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message
        } else if (typeof error.response.data === 'object') {
          // Handle field-specific errors
          const fieldErrors = Object.entries(error.response.data)
            .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors[0] : errors}`)
            .join(', ')
          errorMessage = fieldErrors || JSON.stringify(error.response.data)
        }
      }
      showToast(errorMessage, 'error')
    }
  }

  const handleTransaction = async (data) => {
    try {
      await api.post(`/inventory/items/${selectedItemForTransaction.id}/adjust_stock/`, {
        type: data.type,
        quantity: parseFloat(data.quantity),
        notes: data.notes
      })
      showToast('Stock adjusted successfully', 'success')
      setIsTransactionModalOpen(false)
      transactionForm.reset()
      setSelectedItemForTransaction(null)
      fetchInventory()
      fetchTransactions()
    } catch (error) {
      showToast('Failed to adjust stock', 'error')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return
    
    try {
      await api.delete(`/inventory/items/${id}/`)
      showToast('Item deleted successfully', 'success')
      fetchInventory()
    } catch (error) {
      showToast('Failed to delete item', 'error')
    }
  }

  const handleEdit = (item) => {
    setSelectedItem(item)
    itemForm.reset({
      name: item.name,
      description: item.description,
      sku: item.sku,
      category: item.category,
      unit: item.unit,
      current_stock: item.current_stock,
      minimum_stock: item.minimum_stock,
      maximum_stock: item.maximum_stock,
      unit_price: item.unit_price,
      supplier: item.supplier,
      location: item.location
    })
    setIsModalOpen(true)
  }

  const filteredItems = items.filter(item => {
    const matchesSearch = 
      item.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description?.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  const lowStockItems = items.filter(item => item.is_low_stock)
  const totalStockValue = items.reduce((sum, item) => sum + (item.stock_value || 0), 0)

  const chartData = items.slice(0, 10).map(item => ({
    name: item.name.length > 15 ? item.name.substring(0, 15) + '...' : item.name,
    stock: parseFloat(item.current_stock),
    value: parseFloat(item.stock_value || 0)
  }))

  const categoryData = items.reduce((acc, item) => {
    const cat = item.category || 'other'
    acc[cat] = (acc[cat] || 0) + 1
    return acc
  }, {})

  const pieData = Object.entries(categoryData).map(([name, value]) => ({ name, value }))
  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6']

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Inventory Management</h1>
          <p className="mt-1 text-sm text-gray-500">Track and manage your inventory items</p>
        </div>
        <Button onClick={() => { setSelectedItem(null); itemForm.reset(); setIsModalOpen(true) }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Item
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Items</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{items.length}</p>
              </div>
              <Package className="w-8 h-8 text-blue-500" />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Low Stock</p>
                <p className="mt-1 text-2xl font-bold text-red-600">{lowStockItems.length}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Value</p>
                <p className="mt-1 text-2xl font-bold text-green-600">£{totalStockValue.toFixed(2)}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-500" />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Transactions</p>
                <p className="mt-1 text-2xl font-bold text-purple-600">{transactions.length}</p>
              </div>
              <TrendingDown className="w-8 h-8 text-purple-500" />
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Top 10 Items by Stock</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="stock" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-gray-900">Items by Category</h3>
          </CardHeader>
          <CardBody>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search items..."
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
              <option value="equipment">Equipment</option>
              <option value="consumable">Consumable</option>
              <option value="furniture">Furniture</option>
              <option value="decor">Decor</option>
              <option value="audio_visual">Audio Visual</option>
              <option value="catering">Catering</option>
              <option value="other">Other</option>
            </Select>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showLowStock}
                onChange={(e) => setShowLowStock(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Show Low Stock Only</span>
            </label>
            <Button variant="outline" onClick={() => { setSearchTerm(''); setFilterCategory(''); setShowLowStock(false) }}>
              Clear Filters
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Inventory Table */}
      {loading ? (
        <Loading className="py-12" />
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No items found</p>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SKU</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Min Stock</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{item.name}</div>
                      {item.description && (
                        <div className="text-sm text-gray-500 truncate max-w-xs">{item.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900 font-mono">{item.sku}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        {item.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-gray-900">
                        {item.current_stock} {item.unit}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-500">
                        {item.minimum_stock} {item.unit}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-green-600">
                        £{item.stock_value?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {item.is_low_stock ? (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          Low Stock
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                          In Stock
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSelectedItemForTransaction(item)
                            transactionForm.reset({ type: 'in', quantity: '', notes: '' })
                            setIsTransactionModalOpen(true)
                          }}
                        >
                          Adjust
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleEdit(item)}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => handleDelete(item.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); itemForm.reset(); setSelectedItem(null) }}
        title={selectedItem ? 'Edit Item' : 'Add New Item'}
        size="lg"
      >
        <form onSubmit={itemForm.handleSubmit(onSubmit, onItemFormError)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Item Name"
              {...itemForm.register('name', { required: 'Name is required' })}
              error={itemForm.formState.errors.name?.message}
            />
            <Input
              label="SKU"
              {...itemForm.register('sku', { required: 'SKU is required' })}
              error={itemForm.formState.errors.sku?.message}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              {...itemForm.register('description')}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Category"
              {...itemForm.register('category', { required: 'Category is required' })}
              error={itemForm.formState.errors.category?.message}
            >
              <option value="">Select category</option>
              <option value="equipment">Equipment</option>
              <option value="consumable">Consumable</option>
              <option value="furniture">Furniture</option>
              <option value="decor">Decor</option>
              <option value="audio_visual">Audio Visual</option>
              <option value="catering">Catering</option>
              <option value="other">Other</option>
            </Select>

            <Select
              label="Unit"
              {...itemForm.register('unit', { required: 'Unit is required' })}
              error={itemForm.formState.errors.unit?.message}
            >
              <option value="piece">Piece</option>
              <option value="set">Set</option>
              <option value="box">Box</option>
              <option value="kg">Kilogram</option>
              <option value="liter">Liter</option>
              <option value="meter">Meter</option>
            </Select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Current Stock"
              type="number"
              step="0.01"
              {...itemForm.register('current_stock', { 
                required: 'Current stock is required', 
                min: { value: 0, message: 'Must be 0 or greater' },
                valueAsNumber: true
              })}
              error={itemForm.formState.errors.current_stock?.message}
            />
            <Input
              label="Min Stock"
              type="number"
              step="0.01"
              {...itemForm.register('minimum_stock', { 
                required: 'Minimum stock is required', 
                min: { value: 0, message: 'Must be 0 or greater' },
                valueAsNumber: true
              })}
              error={itemForm.formState.errors.minimum_stock?.message}
            />
            <Input
              label="Max Stock"
              type="number"
              step="0.01"
              {...itemForm.register('maximum_stock', { 
                min: { value: 0, message: 'Must be 0 or greater' },
                valueAsNumber: true
              })}
              error={itemForm.formState.errors.maximum_stock?.message}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Unit Price (£)"
              type="number"
              step="0.01"
              {...itemForm.register('unit_price', { 
                required: 'Unit price is required', 
                min: { value: 0, message: 'Must be 0 or greater' },
                valueAsNumber: true
              })}
              error={itemForm.formState.errors.unit_price?.message}
            />
            <Input
              label="Supplier"
              {...itemForm.register('supplier')}
            />
          </div>

          <Input
            label="Location"
            {...itemForm.register('location')}
          />

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => { setIsModalOpen(false); itemForm.reset() }}>
              Cancel
            </Button>
            <Button type="submit">
              {selectedItem ? 'Update Item' : 'Create Item'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Transaction Modal */}
      <Modal
        isOpen={isTransactionModalOpen}
        onClose={() => { setIsTransactionModalOpen(false); transactionForm.reset(); setSelectedItemForTransaction(null) }}
        title={`Adjust Stock - ${selectedItemForTransaction?.name}`}
      >
        <form onSubmit={transactionForm.handleSubmit(handleTransaction, onTransactionFormError)} className="space-y-4">
          <Select
            label="Transaction Type"
            {...transactionForm.register('type', { required: 'Type is required' })}
            error={transactionForm.formState.errors.type?.message}
          >
            <option value="">Select type</option>
            <option value="in">Stock In</option>
            <option value="out">Stock Out</option>
            <option value="adjustment">Adjustment</option>
          </Select>

          <Input
            label="Quantity"
            type="number"
            step="0.01"
            {...transactionForm.register('quantity', { 
              required: 'Quantity is required', 
              min: { value: 0.01, message: 'Must be greater than 0' },
              valueAsNumber: true
            })}
            error={transactionForm.formState.errors.quantity?.message}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              {...transactionForm.register('notes')}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Optional notes about this transaction"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => { setIsTransactionModalOpen(false); transactionForm.reset() }}>
              Cancel
            </Button>
            <Button type="submit">
              Adjust Stock
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default Inventory

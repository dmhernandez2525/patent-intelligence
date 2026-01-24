import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Zap,
  Eye,
  Bell,
  Plus,
  Trash2,
  AlertCircle,
  Loader2,
  Check,
  X,
} from 'lucide-react'
import { api } from '../lib/api'

interface WatchlistItem {
  id: number
  item_type: string
  item_value: string
  name: string | null
  notes: string | null
  notify_expiration: boolean
  notify_maintenance: boolean
  is_active: boolean
  unread_alerts: number
  created_at: string | null
}

interface Alert {
  id: number
  alert_type: string
  priority: string
  title: string
  message: string
  related_patent_number: string | null
  trigger_date: string | null
  is_read: boolean
}

interface AlertSummary {
  total_unread: number
  critical_count: number
  high_count: number
}

function WatchlistPage() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newItem, setNewItem] = useState({
    item_type: 'patent',
    item_value: '',
    name: '',
  })

  const watchlistQuery = useQuery<{ items: WatchlistItem[]; total: number }>({
    queryKey: ['watchlist'],
    queryFn: async () => {
      const resp = await api.get('/watchlist')
      return resp.data
    },
  })

  const alertsQuery = useQuery<{ alerts: Alert[]; total: number }>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const resp = await api.get('/watchlist/alerts', {
        params: { unread_only: true, per_page: 10 },
      })
      return resp.data
    },
  })

  const summaryQuery = useQuery<AlertSummary>({
    queryKey: ['alert-summary'],
    queryFn: async () => {
      const resp = await api.get('/watchlist/alerts/summary')
      return resp.data
    },
  })

  const addMutation = useMutation({
    mutationFn: async (item: typeof newItem) => {
      const resp = await api.post('/watchlist', item)
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      setShowAddForm(false)
      setNewItem({ item_type: 'patent', item_value: '', name: '' })
    },
  })

  const removeMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/watchlist/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })

  const markReadMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/watchlist/alerts/${id}/read`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alert-summary'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })

  const dismissMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/watchlist/alerts/${id}/dismiss`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alert-summary'] })
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (newItem.item_value) {
      addMutation.mutate(newItem)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-primary-600 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-bold text-gray-900">Patent Intelligence</span>
              </Link>
              <nav className="hidden sm:flex items-center gap-4">
                <Link to="/dashboard" className="text-sm font-medium text-gray-600 hover:text-gray-900">Dashboard</Link>
                <Link to="/search" className="text-sm font-medium text-gray-600 hover:text-gray-900">Search</Link>
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
                <Link to="/whitespace" className="text-sm font-medium text-gray-600 hover:text-gray-900">White Space</Link>
                <Link to="/ideas" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ideas</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Eye className="h-6 w-6 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add Item
          </button>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          Track patents, technology areas, and assignees for expiration and maintenance alerts.
        </p>

        {/* Alert Summary */}
        {summaryQuery.data && summaryQuery.data.total_unread > 0 && (
          <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-amber-600" />
              <div>
                <span className="font-semibold text-amber-800">
                  {summaryQuery.data.total_unread} unread alerts
                </span>
                {summaryQuery.data.critical_count > 0 && (
                  <span className="ml-2 text-red-600">
                    ({summaryQuery.data.critical_count} critical)
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Add Form */}
        {showAddForm && (
          <form onSubmit={handleAdd} className="mt-6 rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">Add to Watchlist</h3>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Type</label>
                <select
                  value={newItem.item_type}
                  onChange={(e) => setNewItem({ ...newItem, item_type: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="patent">Patent</option>
                  <option value="cpc_code">CPC Code</option>
                  <option value="assignee">Assignee</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Value</label>
                <input
                  type="text"
                  value={newItem.item_value}
                  onChange={(e) => setNewItem({ ...newItem, item_value: e.target.value })}
                  placeholder={newItem.item_type === 'patent' ? 'US12345678' : newItem.item_type === 'cpc_code' ? 'H01L' : 'Company Name'}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Name (optional)</label>
                <input
                  type="text"
                  value={newItem.name}
                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                  placeholder="Display name"
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                disabled={addMutation.isPending || !newItem.item_value}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {addMutation.isPending ? 'Adding...' : 'Add'}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Watchlist Items */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Watched Items</h2>

            {watchlistQuery.isLoading && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </div>
            )}

            {watchlistQuery.data && watchlistQuery.data.items.length === 0 && (
              <div className="mt-4 rounded-lg border border-dashed border-gray-300 p-8 text-center">
                <Eye className="mx-auto h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">No items in watchlist</p>
                <p className="text-xs text-gray-400">Add patents or CPC codes to track</p>
              </div>
            )}

            {watchlistQuery.data && watchlistQuery.data.items.length > 0 && (
              <div className="mt-4 space-y-3">
                {watchlistQuery.data.items.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-gray-200 bg-white p-4 hover:border-primary-200"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            {item.name || item.item_value}
                          </span>
                          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                            {item.item_type}
                          </span>
                          {item.unread_alerts > 0 && (
                            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                              {item.unread_alerts} alerts
                            </span>
                          )}
                        </div>
                        {item.name && (
                          <div className="text-xs text-gray-500 mt-1">{item.item_value}</div>
                        )}
                      </div>
                      <button
                        onClick={() => removeMutation.mutate(item.id)}
                        className="text-gray-400 hover:text-red-600"
                        title="Remove from watchlist"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="mt-2 flex gap-3 text-xs text-gray-500">
                      {item.notify_expiration && <span>Expiration alerts</span>}
                      {item.notify_maintenance && <span>Maintenance alerts</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Alerts */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Recent Alerts</h2>

            {alertsQuery.isLoading && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </div>
            )}

            {alertsQuery.data && alertsQuery.data.alerts.length === 0 && (
              <div className="mt-4 rounded-lg border border-dashed border-gray-300 p-8 text-center">
                <Bell className="mx-auto h-8 w-8 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">No unread alerts</p>
                <p className="text-xs text-gray-400">Alerts will appear here when triggered</p>
              </div>
            )}

            {alertsQuery.data && alertsQuery.data.alerts.length > 0 && (
              <div className="mt-4 space-y-3">
                {alertsQuery.data.alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`rounded-lg border p-4 ${getPriorityColor(alert.priority)}`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4" />
                          <span className="font-medium">{alert.title}</span>
                        </div>
                        <p className="mt-1 text-sm">{alert.message}</p>
                        {alert.related_patent_number && (
                          <p className="mt-1 text-xs opacity-75">
                            Patent: {alert.related_patent_number}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => markReadMutation.mutate(alert.id)}
                          className="rounded p-1 hover:bg-white/50"
                          title="Mark as read"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => dismissMutation.mutate(alert.id)}
                          className="rounded p-1 hover:bg-white/50"
                          title="Dismiss"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default WatchlistPage

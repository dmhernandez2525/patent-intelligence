import { Link } from 'react-router-dom'
import { Clock, Zap, AlertTriangle } from 'lucide-react'

function ExpirationPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
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
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Expiration Intelligence</h1>
        <p className="mt-1 text-sm text-gray-600">
          Track patent expirations, maintenance fees, and discover lapsed patent opportunities.
        </p>

        {/* Time Period Tabs */}
        <div className="mt-6 flex gap-2 border-b border-gray-200">
          {['30 Days', '90 Days', '1 Year', 'Lapsed'].map((period, idx) => (
            <button
              key={period}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                idx === 0
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {period}
            </button>
          ))}
        </div>

        {/* Summary Cards */}
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-800">Expiring in 30 Days</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-yellow-900">0</p>
          </div>
          <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-orange-600" />
              <span className="text-sm font-medium text-orange-800">Expiring in 90 Days</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-orange-900">0</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-red-600" />
              <span className="text-sm font-medium text-red-800">Recently Lapsed</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-red-900">0</p>
          </div>
        </div>

        {/* Expiration List */}
        <div className="mt-8">
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
            <Clock className="mx-auto h-12 w-12 text-gray-300" />
            <h3 className="mt-4 text-sm font-medium text-gray-900">No expiration data available</h3>
            <p className="mt-2 text-sm text-gray-500">
              Patent expiration tracking will be available once data ingestion is complete.
              50% of patents lapse due to non-payment of maintenance fees.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default ExpirationPage

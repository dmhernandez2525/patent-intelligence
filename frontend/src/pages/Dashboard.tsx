import { Link } from 'react-router-dom'
import { Search, Clock, TrendingUp, Lightbulb, Zap, Sparkles, Map } from 'lucide-react'

function Dashboard() {
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
                <Link to="/search" className="text-sm font-medium text-gray-600 hover:text-gray-900">Search</Link>
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
                <Link to="/similarity" className="text-sm font-medium text-gray-600 hover:text-gray-900">Similarity</Link>
                <Link to="/trends" className="text-sm font-medium text-gray-600 hover:text-gray-900">Trends</Link>
                <Link to="/whitespace" className="text-sm font-medium text-gray-600 hover:text-gray-900">White Space</Link>
                <Link to="/ideas" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ideas</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      {/* Dashboard Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">Overview of your patent intelligence platform.</p>

        {/* Stats Grid */}
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={<Search className="h-5 w-5" />} label="Total Patents" value="0" change="Data ingestion pending" />
          <StatCard icon={<Clock className="h-5 w-5" />} label="Expiring Soon" value="0" change="Within 90 days" />
          <StatCard icon={<TrendingUp className="h-5 w-5" />} label="Trending CPCs" value="--" change="Analysis pending" />
          <StatCard icon={<Lightbulb className="h-5 w-5" />} label="Ideas Generated" value="0" change="AI-powered" />
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <ActionCard
              to="/search"
              title="Search Patents"
              description="Search 200M+ patents using semantic or keyword search"
              icon={<Search className="h-5 w-5" />}
            />
            <ActionCard
              to="/expiration"
              title="Expiration Tracker"
              description="Monitor upcoming patent expirations and lapsed patents"
              icon={<Clock className="h-5 w-5" />}
            />
            <ActionCard
              to="/trends"
              title="Trend Analysis"
              description="View technology trends and citation networks"
              icon={<TrendingUp className="h-5 w-5" />}
            />
            <ActionCard
              to="/whitespace"
              title="White Space"
              description="Discover technology gaps and untapped opportunities"
              icon={<Map className="h-5 w-5" />}
            />
            <ActionCard
              to="/ideas"
              title="AI Ideas"
              description="Generate invention ideas from patent landscape analysis"
              icon={<Sparkles className="h-5 w-5" />}
            />
          </div>
        </div>

        {/* System Status */}
        <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
          <div className="mt-4 space-y-3">
            <StatusRow label="API Server" status="operational" />
            <StatusRow label="Database" status="operational" />
            <StatusRow label="USPTO Ingestion" status="pending" />
            <StatusRow label="EPO Integration" status="pending" />
            <StatusRow label="Embedding Service" status="pending" />
          </div>
        </div>
      </main>
    </div>
  )
}

function StatCard({ icon, label, value, change }: { icon: React.ReactNode; label: string; value: string; change: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-100 text-primary-600">
          {icon}
        </div>
        <div>
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-gray-500">{change}</p>
    </div>
  )
}

function ActionCard({ to, title, description, icon }: { to: string; title: string; description: string; icon: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-5 hover:border-primary-300 hover:shadow-sm transition-all"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-600 flex-shrink-0">
        {icon}
      </div>
      <div>
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
      </div>
    </Link>
  )
}

function StatusRow({ label, status }: { label: string; status: 'operational' | 'pending' | 'error' }) {
  const statusColors = {
    operational: 'bg-green-500',
    pending: 'bg-yellow-400',
    error: 'bg-red-500',
  }

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-700">{label}</span>
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${statusColors[status]}`} />
        <span className="text-xs text-gray-500 capitalize">{status}</span>
      </div>
    </div>
  )
}

export default Dashboard

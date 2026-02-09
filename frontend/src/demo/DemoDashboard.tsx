import { Link } from 'react-router-dom'
import { Search, Clock, TrendingUp, Sparkles, Map, Eye, Bell } from 'lucide-react'
import { DemoLayout } from './DemoLayout'
import { demoDashboardStats, demoSystemStatus, demoAlertSummary } from './demoData'

export function DemoDashboard() {
  const stats = demoDashboardStats
  const status = demoSystemStatus

  const formatNumber = (n: number | undefined) => {
    if (n === undefined) return '--'
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
    return n.toString()
  }

  return (
    <DemoLayout
      title="Dashboard"
      description="Overview of your patent intelligence platform."
      alertCount={demoAlertSummary.total_unread}
    >
      {/* Stats Grid */}
      <div className="mt-6 sm:mt-8 grid grid-cols-2 gap-3 sm:gap-6 lg:grid-cols-4">
        <StatCard
          icon={<Search className="h-5 w-5" />}
          label="Total Patents"
          value={formatNumber(stats.patents.total)}
          change="In database"
        />
        <StatCard
          icon={<Clock className="h-5 w-5" />}
          label="Expiring Soon"
          value={formatNumber(stats.patents.expiring_90_days)}
          change="Within 90 days"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Top CPC"
          value={stats.trends.top_cpc[0]?.cpc_code || '--'}
          change={`${formatNumber(stats.trends.top_cpc[0]?.count)} patents`}
        />
        <StatCard
          icon={<Bell className="h-5 w-5" />}
          label="Watchlist Alerts"
          value={formatNumber(stats.watchlist.unread_alerts)}
          change={`${stats.watchlist.count} items tracked`}
        />
      </div>

      {/* Quick Actions */}
      <div className="mt-6 sm:mt-8">
        <h2 className="text-base sm:text-lg font-semibold text-gray-900">Quick Actions</h2>
        <div className="mt-3 sm:mt-4 grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <ActionCard
            to="/demo/search"
            title="Search Patents"
            description="Search patents using semantic or keyword search"
            icon={<Search className="h-5 w-5" />}
          />
          <ActionCard
            to="/demo/expiration"
            title="Expiration Tracker"
            description="Monitor upcoming patent expirations and lapsed patents"
            icon={<Clock className="h-5 w-5" />}
          />
          <ActionCard
            to="/demo/trends"
            title="Trend Analysis"
            description="View technology trends and citation networks"
            icon={<TrendingUp className="h-5 w-5" />}
          />
          <ActionCard
            to="/demo/whitespace"
            title="White Space"
            description="Discover technology gaps and untapped opportunities"
            icon={<Map className="h-5 w-5" />}
          />
          <ActionCard
            to="/demo/ideas"
            title="AI Ideas"
            description="Generate invention ideas from patent landscape analysis"
            icon={<Sparkles className="h-5 w-5" />}
          />
          <ActionCard
            to="/demo/watchlist"
            title="Watchlist"
            description="Track patents and get alerts for expirations"
            icon={<Eye className="h-5 w-5" />}
          />
        </div>
      </div>

      {/* System Status */}
      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
        <div className="mt-4 space-y-3">
          <StatusRow label="API Server" status={status.api_server} />
          <StatusRow label="Database" status={status.database} />
          <StatusRow label="USPTO Ingestion" status={status.uspto_ingestion} />
          <StatusRow label="EPO Integration" status={status.epo_integration} />
          <StatusRow label="Embedding Service" status={status.embedding_service} />
        </div>
      </div>
    </DemoLayout>
  )
}

function StatCard({ icon, label, value, change }: { icon: React.ReactNode; label: string; value: string; change: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 sm:p-5">
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-lg bg-primary-100 text-primary-600 shrink-0">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs sm:text-sm text-gray-600 truncate">{label}</p>
          <p className="text-lg sm:text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
      <p className="mt-1 sm:mt-2 text-[10px] sm:text-xs text-gray-500 truncate">{change}</p>
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

function StatusRow({ label, status }: { label: string; status: string }) {
  const statusColors: Record<string, string> = {
    operational: 'bg-green-500',
    healthy: 'bg-green-500',
    pending: 'bg-yellow-400',
    unknown: 'bg-gray-400',
    error: 'bg-red-500',
    unhealthy: 'bg-red-500',
  }

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-700">{label}</span>
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${statusColors[status] || 'bg-gray-400'}`} />
        <span className="text-xs text-gray-500 capitalize">{status}</span>
      </div>
    </div>
  )
}

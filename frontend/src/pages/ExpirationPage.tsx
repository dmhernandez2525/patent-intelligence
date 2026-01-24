import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Clock,
  Zap,
  AlertTriangle,
  Calendar,
  Building,
  Tag,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  TrendingDown,
  BarChart3,
  Filter,
} from 'lucide-react'
import { api } from '../lib/api'

interface ExpiringPatent {
  patent_number: string
  title: string
  abstract: string | null
  expiration_date: string | null
  filing_date: string | null
  grant_date: string | null
  assignee_organization: string | null
  cpc_codes: string[] | null
  country: string
  status: string
  days_until_expiration: number
  maintenance_fee_status: string
  next_fee_date: string | null
  next_fee_amount: number | null
  citation_count: number | null
  patent_type: string | null
}

interface MaintenanceFee {
  patent_number: string
  title: string
  assignee_organization: string | null
  fee_year: number
  due_date: string
  grace_period_end: string | null
  amount_usd: number | null
  days_until_due: number
  status: string
}

interface ExpirationStats {
  expiring_30_days: number
  expiring_90_days: number
  expiring_180_days: number
  expiring_365_days: number
  recently_lapsed: number
  pending_maintenance_fees: number
  top_sectors: { cpc_code: string; count: number }[]
  monthly_timeline: { month: string; count: number }[]
}

interface DashboardResponse {
  stats: ExpirationStats
  expiring_soon: ExpiringPatent[]
  recently_lapsed: ExpiringPatent[]
  upcoming_fees: MaintenanceFee[]
}

interface ListResponse {
  patents: ExpiringPatent[]
  total: number
  page: number
  per_page: number
}

type TabType = 'overview' | 'expiring' | 'lapsed' | 'fees'

function ExpirationPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [days, setDays] = useState(90)
  const [country, setCountry] = useState('')
  const [cpcCode, setCpcCode] = useState('')
  const [assignee, setAssignee] = useState('')
  const [page, setPage] = useState(1)

  const { data: dashboard, isLoading: dashLoading } = useQuery<DashboardResponse>({
    queryKey: ['expiration-dashboard', country],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (country) params.set('country', country)
      const resp = await api.get(`/expiration/dashboard?${params}`)
      return resp.data
    },
  })

  const { data: expiringList, isLoading: expiringLoading } = useQuery<ListResponse>({
    queryKey: ['expiration-upcoming', days, country, cpcCode, assignee, page],
    queryFn: async () => {
      const params = new URLSearchParams({
        days: days.toString(),
        page: page.toString(),
        per_page: '20',
      })
      if (country) params.set('country', country)
      if (cpcCode) params.set('cpc_code', cpcCode)
      if (assignee) params.set('assignee', assignee)
      const resp = await api.get(`/expiration/upcoming?${params}`)
      return resp.data
    },
    enabled: activeTab === 'expiring',
  })

  const { data: lapsedList, isLoading: lapsedLoading } = useQuery<ListResponse>({
    queryKey: ['expiration-lapsed', country, cpcCode, assignee, page],
    queryFn: async () => {
      const params = new URLSearchParams({
        days_back: '365',
        page: page.toString(),
        per_page: '20',
      })
      if (country) params.set('country', country)
      if (cpcCode) params.set('cpc_code', cpcCode)
      if (assignee) params.set('assignee', assignee)
      const resp = await api.get(`/expiration/lapsed?${params}`)
      return resp.data
    },
    enabled: activeTab === 'lapsed',
  })

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'expiring', label: 'Expiring Soon' },
    { id: 'lapsed', label: 'Lapsed' },
    { id: 'fees', label: 'Maintenance Fees' },
  ]

  const stats = dashboard?.stats

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
                <Link to="/similarity" className="text-sm font-medium text-gray-600 hover:text-gray-900">Similarity</Link>
                <Link to="/trends" className="text-sm font-medium text-gray-600 hover:text-gray-900">Trends</Link>
                <Link to="/ideas" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ideas</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Expiration Intelligence</h1>
        <p className="mt-1 text-sm text-gray-600">
          Track patent expirations, maintenance fees, and discover lapsed patent opportunities.
          50% of patents lapse due to non-payment of maintenance fees.
        </p>

        {/* Tabs */}
        <div className="mt-6 flex gap-1 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setPage(1) }}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="mt-6 space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={<AlertTriangle className="h-5 w-5 text-yellow-600" />}
                label="Expiring in 30 Days"
                value={stats?.expiring_30_days ?? 0}
                bgColor="bg-yellow-50"
                borderColor="border-yellow-200"
                textColor="text-yellow-900"
              />
              <StatCard
                icon={<Clock className="h-5 w-5 text-orange-600" />}
                label="Expiring in 90 Days"
                value={stats?.expiring_90_days ?? 0}
                bgColor="bg-orange-50"
                borderColor="border-orange-200"
                textColor="text-orange-900"
              />
              <StatCard
                icon={<TrendingDown className="h-5 w-5 text-red-600" />}
                label="Recently Lapsed"
                value={stats?.recently_lapsed ?? 0}
                bgColor="bg-red-50"
                borderColor="border-red-200"
                textColor="text-red-900"
              />
              <StatCard
                icon={<DollarSign className="h-5 w-5 text-blue-600" />}
                label="Pending Fees (180d)"
                value={stats?.pending_maintenance_fees ?? 0}
                bgColor="bg-blue-50"
                borderColor="border-blue-200"
                textColor="text-blue-900"
              />
            </div>

            {/* Timeline Chart */}
            {stats?.monthly_timeline && stats.monthly_timeline.length > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <BarChart3 className="h-4 w-4" />
                  <span>Expiration Timeline (Next 12 Months)</span>
                </div>
                <div className="mt-4 flex items-end gap-1 h-32">
                  {stats.monthly_timeline.map((entry, idx) => {
                    const maxCount = Math.max(...stats.monthly_timeline.map(e => e.count), 1)
                    const height = (entry.count / maxCount) * 100
                    const monthLabel = new Date(entry.month + 'T00:00:00').toLocaleDateString('en', { month: 'short' })
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                        <span className="text-xs text-gray-500">{entry.count || ''}</span>
                        <div
                          className="w-full rounded-t bg-primary-400 transition-all hover:bg-primary-500"
                          style={{ height: `${Math.max(height, 2)}%` }}
                          title={`${monthLabel}: ${entry.count} patents`}
                        />
                        <span className="text-xs text-gray-400">{monthLabel}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Top Sectors + Expiring Soon side by side */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Top Sectors */}
              {stats?.top_sectors && stats.top_sectors.length > 0 && (
                <div className="rounded-lg border border-gray-200 bg-white p-5">
                  <h3 className="text-sm font-medium text-gray-700">Top Sectors Expiring (90 Days)</h3>
                  <div className="mt-3 space-y-2">
                    {stats.top_sectors.map((sector) => (
                      <div key={sector.cpc_code} className="flex items-center justify-between">
                        <span className="text-sm font-mono text-gray-600">{sector.cpc_code}</span>
                        <span className="text-sm font-medium text-gray-900">{sector.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expiring Soon Preview */}
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h3 className="text-sm font-medium text-gray-700">Expiring Soon</h3>
                {dashLoading ? (
                  <div className="mt-4 flex justify-center py-4">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
                  </div>
                ) : (dashboard?.expiring_soon?.length ?? 0) === 0 ? (
                  <p className="mt-3 text-sm text-gray-500">No patents expiring in the next 30 days.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {dashboard?.expiring_soon.slice(0, 5).map((p) => (
                      <div key={p.patent_number} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-primary-600 shrink-0">{p.patent_number}</span>
                          <span className="text-gray-600 truncate">{p.title}</span>
                        </div>
                        <span className="text-xs text-orange-600 font-medium shrink-0 ml-2">
                          {p.days_until_expiration}d
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Upcoming Fees Preview */}
            {(dashboard?.upcoming_fees?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h3 className="text-sm font-medium text-gray-700">Upcoming Maintenance Fees</h3>
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500 uppercase">
                        <th className="pb-2 pr-4">Patent</th>
                        <th className="pb-2 pr-4">Year</th>
                        <th className="pb-2 pr-4">Due Date</th>
                        <th className="pb-2 pr-4">Amount</th>
                        <th className="pb-2">Days Left</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {dashboard?.upcoming_fees.slice(0, 5).map((fee, idx) => (
                        <tr key={idx}>
                          <td className="py-2 pr-4 font-mono text-primary-600">{fee.patent_number}</td>
                          <td className="py-2 pr-4">{fee.fee_year}</td>
                          <td className="py-2 pr-4">{fee.due_date}</td>
                          <td className="py-2 pr-4">{fee.amount_usd ? `$${fee.amount_usd.toLocaleString()}` : '--'}</td>
                          <td className="py-2">
                            <span className={`font-medium ${fee.days_until_due <= 30 ? 'text-red-600' : 'text-gray-700'}`}>
                              {fee.days_until_due}d
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Empty state */}
            {!dashLoading && !stats?.expiring_30_days && !stats?.expiring_90_days && !stats?.recently_lapsed && (
              <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
                <Clock className="mx-auto h-12 w-12 text-gray-300" />
                <h3 className="mt-4 text-sm font-medium text-gray-900">No expiration data available</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Patent expiration tracking will populate once data ingestion adds patents with expiration dates.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Expiring Soon Tab */}
        {activeTab === 'expiring' && (
          <div className="mt-6">
            <FilterBar
              days={days}
              onDaysChange={setDays}
              country={country}
              onCountryChange={setCountry}
              cpcCode={cpcCode}
              onCpcCodeChange={setCpcCode}
              assignee={assignee}
              onAssigneeChange={setAssignee}
              showDays
            />
            <PatentList
              patents={expiringList?.patents}
              total={expiringList?.total ?? 0}
              page={page}
              onPageChange={setPage}
              isLoading={expiringLoading}
              emptyMessage="No patents expiring in the selected time window."
            />
          </div>
        )}

        {/* Lapsed Tab */}
        {activeTab === 'lapsed' && (
          <div className="mt-6">
            <FilterBar
              country={country}
              onCountryChange={setCountry}
              cpcCode={cpcCode}
              onCpcCodeChange={setCpcCode}
              assignee={assignee}
              onAssigneeChange={setAssignee}
            />
            <PatentList
              patents={lapsedList?.patents}
              total={lapsedList?.total ?? 0}
              page={page}
              onPageChange={setPage}
              isLoading={lapsedLoading}
              emptyMessage="No recently lapsed patents found."
              showLapsed
            />
          </div>
        )}

        {/* Maintenance Fees Tab */}
        {activeTab === 'fees' && (
          <div className="mt-6">
            <FeesList fees={dashboard?.upcoming_fees ?? []} isLoading={dashLoading} />
          </div>
        )}
      </main>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  bgColor,
  borderColor,
  textColor,
}: {
  icon: React.ReactNode
  label: string
  value: number
  bgColor: string
  borderColor: string
  textColor: string
}) {
  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-4`}>
      <div className="flex items-center gap-2">
        {icon}
        <span className={`text-sm font-medium ${textColor}`}>{label}</span>
      </div>
      <p className={`mt-2 text-2xl font-bold ${textColor}`}>{value.toLocaleString()}</p>
    </div>
  )
}

function FilterBar({
  days,
  onDaysChange,
  country,
  onCountryChange,
  cpcCode,
  onCpcCodeChange,
  assignee,
  onAssigneeChange,
  showDays = false,
}: {
  days?: number
  onDaysChange?: (d: number) => void
  country: string
  onCountryChange: (c: string) => void
  cpcCode: string
  onCpcCodeChange: (c: string) => void
  assignee: string
  onAssigneeChange: (a: string) => void
  showDays?: boolean
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 mb-4">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
        <Filter className="h-4 w-4" />
        <span>Filters</span>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
        {showDays && onDaysChange && (
          <select
            value={days}
            onChange={(e) => onDaysChange(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value={30}>Next 30 Days</option>
            <option value={90}>Next 90 Days</option>
            <option value={180}>Next 180 Days</option>
            <option value={365}>Next 1 Year</option>
            <option value={730}>Next 2 Years</option>
          </select>
        )}
        <select
          value={country}
          onChange={(e) => onCountryChange(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Countries</option>
          <option value="US">United States</option>
          <option value="EP">Europe (EPO)</option>
          <option value="JP">Japan</option>
          <option value="CN">China</option>
          <option value="KR">South Korea</option>
        </select>
        <input
          type="text"
          value={cpcCode}
          onChange={(e) => onCpcCodeChange(e.target.value)}
          placeholder="CPC Code (e.g., H01L)"
          className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
        />
        <input
          type="text"
          value={assignee}
          onChange={(e) => onAssigneeChange(e.target.value)}
          placeholder="Assignee"
          className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
        />
      </div>
    </div>
  )
}

function PatentList({
  patents,
  total,
  page,
  onPageChange,
  isLoading,
  emptyMessage,
  showLapsed = false,
}: {
  patents: ExpiringPatent[] | undefined
  total: number
  page: number
  onPageChange: (p: number) => void
  isLoading: boolean
  emptyMessage: string
  showLapsed?: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    )
  }

  if (!patents || patents.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
        <Clock className="mx-auto h-12 w-12 text-gray-300" />
        <h3 className="mt-4 text-sm font-medium text-gray-900">No results</h3>
        <p className="mt-2 text-sm text-gray-500">{emptyMessage}</p>
      </div>
    )
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <>
      <p className="text-sm text-gray-600 mb-3">
        Showing {((page - 1) * 20) + 1}-{Math.min(page * 20, total)} of{' '}
        <span className="font-medium">{total.toLocaleString()}</span> patents
      </p>
      <div className="space-y-3">
        {patents.map((patent) => (
          <ExpirationCard key={patent.patent_number} patent={patent} showLapsed={showLapsed} />
        ))}
      </div>
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </>
  )
}

function ExpirationCard({ patent, showLapsed }: { patent: ExpiringPatent; showLapsed?: boolean }) {
  const urgencyColor = patent.days_until_expiration <= 30
    ? 'text-red-600 bg-red-50 border-red-200'
    : patent.days_until_expiration <= 90
      ? 'text-orange-600 bg-orange-50 border-orange-200'
      : 'text-yellow-700 bg-yellow-50 border-yellow-200'

  const feeStatusBadge: Record<string, string> = {
    overdue: 'bg-red-100 text-red-700',
    due_soon: 'bg-orange-100 text-orange-700',
    current: 'bg-green-100 text-green-700',
    all_paid: 'bg-green-100 text-green-700',
    no_fees: 'bg-gray-100 text-gray-600',
    unknown: 'bg-gray-100 text-gray-500',
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-primary-200 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-mono text-primary-600">{patent.patent_number}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              patent.status === 'active' ? 'bg-green-100 text-green-700' :
              patent.status === 'lapsed' ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            }`}>
              {patent.status}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${feeStatusBadge[patent.maintenance_fee_status] || feeStatusBadge.unknown}`}>
              fees: {patent.maintenance_fee_status.replace('_', ' ')}
            </span>
            <span className="text-xs text-gray-400">{patent.country}</span>
          </div>
          <h3 className="mt-1 text-base font-semibold text-gray-900 line-clamp-2">{patent.title}</h3>
          {patent.abstract && (
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">{patent.abstract}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
            {patent.assignee_organization && (
              <span className="flex items-center gap-1">
                <Building className="h-3 w-3" />
                {patent.assignee_organization}
              </span>
            )}
            {patent.expiration_date && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Expires: {patent.expiration_date}
              </span>
            )}
            {patent.cpc_codes && patent.cpc_codes.length > 0 && (
              <span className="flex items-center gap-1">
                <Tag className="h-3 w-3" />
                {patent.cpc_codes.slice(0, 3).join(', ')}
                {patent.cpc_codes.length > 3 && ` +${patent.cpc_codes.length - 3}`}
              </span>
            )}
            {patent.next_fee_date && (
              <span className="flex items-center gap-1">
                <DollarSign className="h-3 w-3" />
                Next fee: {patent.next_fee_date}
                {patent.next_fee_amount && ` ($${patent.next_fee_amount.toLocaleString()})`}
              </span>
            )}
          </div>
        </div>
        <div className={`ml-4 rounded-lg border px-3 py-2 text-center ${showLapsed ? 'text-red-600 bg-red-50 border-red-200' : urgencyColor}`}>
          <div className="text-xs font-medium">
            {showLapsed ? 'Expired' : 'Expires in'}
          </div>
          <div className="text-lg font-bold">
            {showLapsed ? Math.abs(patent.days_until_expiration) : patent.days_until_expiration}
          </div>
          <div className="text-xs">{showLapsed ? 'days ago' : 'days'}</div>
        </div>
      </div>
    </div>
  )
}

function FeesList({ fees, isLoading }: { fees: MaintenanceFee[]; isLoading?: boolean }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    )
  }

  if (fees.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
        <DollarSign className="mx-auto h-12 w-12 text-gray-300" />
        <h3 className="mt-4 text-sm font-medium text-gray-900">No upcoming maintenance fees</h3>
        <p className="mt-2 text-sm text-gray-500">
          Maintenance fee deadlines will appear once patent data with fee schedules is ingested.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patent</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fee Year</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Left</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {fees.map((fee, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-mono text-primary-600 whitespace-nowrap">{fee.patent_number}</td>
              <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate">{fee.title}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{fee.assignee_organization || '--'}</td>
              <td className="px-4 py-3 text-sm text-gray-700 text-center">{fee.fee_year}</td>
              <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{fee.due_date}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{fee.amount_usd ? `$${fee.amount_usd.toLocaleString()}` : '--'}</td>
              <td className="px-4 py-3 whitespace-nowrap">
                <span className={`text-sm font-medium ${
                  fee.days_until_due <= 30 ? 'text-red-600' :
                  fee.days_until_due <= 60 ? 'text-orange-600' :
                  'text-gray-700'
                }`}>
                  {fee.days_until_due} days
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ExpirationPage

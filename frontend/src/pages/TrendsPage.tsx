import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Zap,
  TrendingUp,
  GitBranch,
  Building,
  Search,
  Loader2,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { api } from '../lib/api'

interface YearlyCount {
  year: number
  count: number
}

interface CpcTrend {
  cpc_code: string
  total_patents: number
}

interface GrowthLeader {
  cpc_code: string
  recent_count: number
  earlier_count: number
  growth_rate: number
}

interface TopAssignee {
  assignee: string
  patent_count: number
}

interface TrendsResponse {
  period: { start_year: number; end_year: number }
  yearly_totals: YearlyCount[]
  top_cpc_trends: CpcTrend[]
  growth_leaders: GrowthLeader[]
  top_assignees: TopAssignee[]
}

interface CitationNode {
  patent_number: string
  title: string | null
  assignee_organization: string | null
  filing_date: string | null
  country: string | null
  status: string | null
  cpc_codes: string[] | null
  citation_count: number | null
  cited_by_count: number | null
  depth: number
}

interface CitationEdge {
  source: string
  target: string
  type: string
}

interface CitationNetworkResponse {
  center: string
  nodes: CitationNode[]
  edges: CitationEdge[]
  total_nodes: number
  total_edges: number
  depth: number
}

interface CitationStatsResponse {
  patent_number: string
  forward_citations: number
  backward_citations: number
  avg_field_citations: number | null
  citation_index: number | null
}

type ViewMode = 'trends' | 'citations'

function TrendsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('trends')

  // Trend filters
  const [cpcPrefix, setCpcPrefix] = useState('')
  const [country, setCountry] = useState('')
  const [years, setYears] = useState(10)

  // Citation inputs
  const [patentNumber, setPatentNumber] = useState('')
  const [depth, setDepth] = useState(2)
  const [maxNodes, setMaxNodes] = useState(50)

  const trendsQuery = useQuery<TrendsResponse>({
    queryKey: ['trends', cpcPrefix, country, years],
    queryFn: async () => {
      const params: Record<string, string | number> = { years }
      if (cpcPrefix) params.cpc_prefix = cpcPrefix
      if (country) params.country = country
      const resp = await api.get('/analysis/trends', { params })
      return resp.data
    },
    enabled: viewMode === 'trends',
  })

  const citationMutation = useMutation<CitationNetworkResponse>({
    mutationFn: async () => {
      const resp = await api.get(`/analysis/citations/${encodeURIComponent(patentNumber)}`, {
        params: { depth, max_nodes: maxNodes },
      })
      return resp.data
    },
  })

  const statsMutation = useMutation<CitationStatsResponse>({
    mutationFn: async () => {
      const resp = await api.get(`/analysis/citations/${encodeURIComponent(patentNumber)}/stats`)
      return resp.data
    },
  })

  const handleCitationSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!patentNumber.trim()) return
    citationMutation.mutate()
    statsMutation.mutate()
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
                <Link to="/similarity" className="text-sm font-medium text-gray-600 hover:text-gray-900">Similarity</Link>
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Citation Network & Trends</h1>
        <p className="mt-1 text-sm text-gray-600">
          Explore technology trends, citation networks, and competitive landscape analysis.
        </p>

        {/* Mode Selector */}
        <div className="mt-6 flex gap-2">
          <button
            onClick={() => setViewMode('trends')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              viewMode === 'trends'
                ? 'bg-primary-100 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            <TrendingUp className="h-4 w-4" />
            Technology Trends
          </button>
          <button
            onClick={() => setViewMode('citations')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              viewMode === 'citations'
                ? 'bg-primary-100 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            <GitBranch className="h-4 w-4" />
            Citation Network
          </button>
        </div>

        {/* Trends View */}
        {viewMode === 'trends' && (
          <div className="mt-6 space-y-6">
            {/* Filters */}
            <div className="flex flex-wrap gap-3 rounded-lg border border-gray-200 bg-white p-4">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <span>CPC Prefix:</span>
                <input
                  type="text"
                  value={cpcPrefix}
                  onChange={(e) => setCpcPrefix(e.target.value)}
                  placeholder="e.g., H01L"
                  className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
                />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <span>Country:</span>
                <input
                  type="text"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  placeholder="e.g., US"
                  className="w-16 rounded border border-gray-300 px-2 py-1 text-xs"
                />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <span>Years:</span>
                <select
                  value={years}
                  onChange={(e) => setYears(Number(e.target.value))}
                  className="rounded border border-gray-300 px-2 py-1 text-xs"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={30}>30</option>
                </select>
              </label>
            </div>

            {trendsQuery.isLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
              </div>
            )}

            {trendsQuery.data && (
              <div className="space-y-6">
                {/* Yearly Totals Bar Chart */}
                <div className="rounded-lg border border-gray-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary-600" />
                    Patent Filings by Year
                  </h2>
                  <div className="mt-4">
                    {trendsQuery.data.yearly_totals.length > 0 ? (
                      <YearlyChart data={trendsQuery.data.yearly_totals} />
                    ) : (
                      <p className="text-sm text-gray-500">No filing data available for this period.</p>
                    )}
                  </div>
                </div>

                {/* Grid: Top CPC + Growth Leaders + Top Assignees */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* Top CPC Trends */}
                  <div className="rounded-lg border border-gray-200 bg-white p-5">
                    <h2 className="text-sm font-semibold text-gray-900">Top Technology Areas</h2>
                    <div className="mt-3 space-y-2">
                      {trendsQuery.data.top_cpc_trends.length > 0 ? (
                        trendsQuery.data.top_cpc_trends.map((item) => (
                          <div key={item.cpc_code} className="flex items-center justify-between text-sm">
                            <span className="font-mono text-xs text-gray-700">{item.cpc_code}</span>
                            <span className="text-gray-500">{item.total_patents.toLocaleString()}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500">No CPC data available.</p>
                      )}
                    </div>
                  </div>

                  {/* Growth Leaders */}
                  <div className="rounded-lg border border-gray-200 bg-white p-5">
                    <h2 className="text-sm font-semibold text-gray-900">Fastest Growing</h2>
                    <div className="mt-3 space-y-2">
                      {trendsQuery.data.growth_leaders.length > 0 ? (
                        trendsQuery.data.growth_leaders.slice(0, 10).map((item) => (
                          <div key={item.cpc_code} className="flex items-center justify-between text-sm">
                            <span className="font-mono text-xs text-gray-700">{item.cpc_code}</span>
                            <span className={`flex items-center gap-1 text-xs font-medium ${
                              item.growth_rate > 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {item.growth_rate > 0 ? (
                                <ArrowUpRight className="h-3 w-3" />
                              ) : (
                                <ArrowDownRight className="h-3 w-3" />
                              )}
                              {(item.growth_rate * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500">No growth data available.</p>
                      )}
                    </div>
                  </div>

                  {/* Top Assignees */}
                  <div className="rounded-lg border border-gray-200 bg-white p-5">
                    <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                      <Building className="h-4 w-4 text-gray-400" />
                      Top Filers
                    </h2>
                    <div className="mt-3 space-y-2">
                      {trendsQuery.data.top_assignees.length > 0 ? (
                        trendsQuery.data.top_assignees.map((item) => (
                          <div key={item.assignee} className="flex items-center justify-between text-sm">
                            <span className="text-gray-700 truncate max-w-[140px]" title={item.assignee}>
                              {item.assignee}
                            </span>
                            <span className="text-gray-500 text-xs">{item.patent_count.toLocaleString()}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500">No assignee data available.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Citations View */}
        {viewMode === 'citations' && (
          <div className="mt-6 space-y-6">
            {/* Search Form */}
            <form onSubmit={handleCitationSearch} className="rounded-lg border border-gray-200 bg-white p-5">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={patentNumber}
                  onChange={(e) => setPatentNumber(e.target.value)}
                  placeholder="Enter patent number (e.g., US-10123456-B2)"
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
                <button
                  type="submit"
                  disabled={citationMutation.isPending}
                  className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white hover:bg-primary-700 transition-colors disabled:opacity-50"
                >
                  {citationMutation.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Search className="h-5 w-5" />
                  )}
                </button>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
                <label className="flex items-center gap-2 text-gray-600">
                  <span>Depth:</span>
                  <select
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    className="rounded border border-gray-300 px-2 py-1 text-xs"
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-gray-600">
                  <span>Max nodes:</span>
                  <select
                    value={maxNodes}
                    onChange={(e) => setMaxNodes(Number(e.target.value))}
                    className="rounded border border-gray-300 px-2 py-1 text-xs"
                  >
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={200}>200</option>
                  </select>
                </label>
              </div>
            </form>

            {/* Citation Stats */}
            {statsMutation.data && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatBox label="Forward Citations" value={statsMutation.data.forward_citations} />
                <StatBox label="Backward Citations" value={statsMutation.data.backward_citations} />
                <StatBox
                  label="Field Average"
                  value={statsMutation.data.avg_field_citations ?? 'N/A'}
                />
                <StatBox
                  label="Citation Index"
                  value={statsMutation.data.citation_index ?? 'N/A'}
                  highlight={statsMutation.data.citation_index !== null && statsMutation.data.citation_index > 1}
                />
              </div>
            )}

            {/* Citation Network */}
            {citationMutation.isPending && (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
              </div>
            )}

            {citationMutation.isError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                Failed to load citation network. Patent may not exist in the database.
              </div>
            )}

            {citationMutation.data && (
              <div className="space-y-4">
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span>Center: <span className="font-mono font-medium text-primary-600">{citationMutation.data.center}</span></span>
                  <span>Nodes: <span className="font-medium">{citationMutation.data.total_nodes}</span></span>
                  <span>Edges: <span className="font-medium">{citationMutation.data.total_edges}</span></span>
                </div>

                {/* Network Nodes by Depth */}
                {[0, 1, 2, 3].map((d) => {
                  const nodesAtDepth = (citationMutation.data?.nodes ?? []).filter((n) => n.depth === d)
                  if (nodesAtDepth.length === 0) return null
                  return (
                    <div key={d}>
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        {d === 0 ? 'Center Patent' : `Depth ${d}`} ({nodesAtDepth.length})
                      </h3>
                      <div className="space-y-2">
                        {nodesAtDepth.map((node) => (
                          <CitationNodeCard key={node.patent_number} node={node} />
                        ))}
                      </div>
                    </div>
                  )
                })}

                {/* Edge Summary */}
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Citation Relationships</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                    {citationMutation.data.edges.map((edge, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="font-mono">{edge.source}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          edge.type === 'cites'
                            ? 'bg-blue-50 text-blue-600'
                            : 'bg-orange-50 text-orange-600'
                        }`}>
                          {edge.type === 'cites' ? 'cites' : 'cited by'}
                        </span>
                        <span className="font-mono">{edge.target}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {!citationMutation.data && !citationMutation.isPending && (
              <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
                <GitBranch className="mx-auto h-12 w-12 text-gray-300" />
                <h3 className="mt-4 text-sm font-medium text-gray-900">Explore Citation Networks</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Enter a patent number to visualize its citation network and see related patents.
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function YearlyChart({ data }: { data: YearlyCount[] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="flex items-end gap-1 h-40">
      {data.map((item) => (
        <div key={item.year} className="flex-1 flex flex-col items-center gap-1">
          <span className="text-[10px] text-gray-500">{item.count}</span>
          <div
            className="w-full bg-primary-500 rounded-t transition-all"
            style={{ height: `${(item.count / maxCount) * 100}%`, minHeight: item.count > 0 ? '4px' : '0' }}
          />
          <span className="text-[10px] text-gray-400 -rotate-45 origin-top-left mt-1">
            {item.year}
          </span>
        </div>
      ))}
    </div>
  )
}

function StatBox({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 text-center ${
      highlight ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
    }`}>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-bold ${highlight ? 'text-green-700' : 'text-gray-900'}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}

function CitationNodeCard({ node }: { node: CitationNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 hover:border-primary-200 transition-colors">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-mono text-primary-600">{node.patent_number}</span>
        {node.status && (
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
            node.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
          }`}>
            {node.status}
          </span>
        )}
        {node.country && <span className="text-xs text-gray-400">{node.country}</span>}
      </div>
      {node.title && (
        <p className="mt-1 text-sm text-gray-800 line-clamp-1">{node.title}</p>
      )}
      <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
        {node.assignee_organization && (
          <span className="flex items-center gap-1">
            <Building className="h-3 w-3" />
            {node.assignee_organization}
          </span>
        )}
        {node.filing_date && <span>Filed: {node.filing_date}</span>}
        {node.cited_by_count != null && <span>Cited by: {node.cited_by_count}</span>}
      </div>
    </div>
  )
}

export default TrendsPage

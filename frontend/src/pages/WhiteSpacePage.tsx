import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Zap,
  Map,
  Target,
  TrendingDown,
  Layers,
  ChevronRight,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { api } from '../lib/api'

interface WhiteSpace {
  cpc_code: string
  section: string
  section_name: string
  historical_patents: number
  recent_patents: number
  decline_ratio: number
  high_impact_count: number
  max_citations: number
  gap_score: number
  opportunity_type: string
}

interface SectionInfo {
  section: string
  name: string
  total_patents: number
  recent_patents: number
  market_share: number
  avg_citations: number
  high_impact_count: number
  momentum: number
  trend: string
}

interface CrossDomainOpportunity {
  cpc_code: string
  section: string
  section_name: string
  patent_count: number
  avg_citations: number
  existing_combinations: number
  opportunity_score: number
  status: string
}

function WhiteSpacePage() {
  const [selectedSection, setSelectedSection] = useState<string | null>(null)
  const [cpcPrefix, setCpcPrefix] = useState('')

  const sectionsQuery = useQuery<{ sections: SectionInfo[] }>({
    queryKey: ['whitespace-sections'],
    queryFn: async () => {
      const resp = await api.get('/whitespace/sections')
      return resp.data
    },
  })

  const gapsQuery = useQuery<{ white_spaces: WhiteSpace[]; total_found: number }>({
    queryKey: ['whitespace-gaps', cpcPrefix],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit: 25 }
      if (cpcPrefix) params.cpc_prefix = cpcPrefix
      const resp = await api.get('/whitespace/gaps', { params })
      return resp.data
    },
  })

  const crossDomainQuery = useQuery<{ opportunities: CrossDomainOpportunity[] }>({
    queryKey: ['whitespace-crossdomain', selectedSection],
    queryFn: async () => {
      if (!selectedSection) return { opportunities: [] }
      const resp = await api.get(`/whitespace/cross-domain/${selectedSection}`)
      return resp.data
    },
    enabled: !!selectedSection,
  })

  const getOpportunityBadge = (type: string) => {
    const badges: Record<string, { label: string; color: string }> = {
      abandoned_goldmine: { label: 'Goldmine', color: 'bg-yellow-100 text-yellow-800' },
      dormant: { label: 'Dormant', color: 'bg-gray-100 text-gray-800' },
      consolidation: { label: 'Consolidating', color: 'bg-blue-100 text-blue-800' },
      emerging_gap: { label: 'Emerging', color: 'bg-green-100 text-green-800' },
      minor_gap: { label: 'Minor', color: 'bg-gray-100 text-gray-600' },
    }
    const badge = badges[type] || { label: type, color: 'bg-gray-100 text-gray-600' }
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.label}
      </span>
    )
  }

  const getTrendIcon = (trend: string) => {
    if (trend === 'growing') return <span className="text-green-600">+</span>
    if (trend === 'declining') return <span className="text-red-600">-</span>
    return <span className="text-gray-400">=</span>
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
                <Link to="/similarity" className="text-sm font-medium text-gray-600 hover:text-gray-900">Similarity</Link>
                <Link to="/trends" className="text-sm font-medium text-gray-600 hover:text-gray-900">Trends</Link>
                <Link to="/ideas" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ideas</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <Map className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-gray-900">White Space Discovery</h1>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          Identify technology gaps and untapped innovation opportunities across the patent landscape.
        </p>

        {/* Section Overview */}
        <div className="mt-6">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Layers className="h-5 w-5 text-gray-400" />
            Technology Landscape
          </h2>
          <p className="text-sm text-gray-500 mt-1">Click a section to explore cross-domain opportunities</p>

          {sectionsQuery.isLoading && (
            <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading sections...
            </div>
          )}

          {sectionsQuery.data && (
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {sectionsQuery.data.sections.map((section) => (
                <button
                  key={section.section}
                  onClick={() => setSelectedSection(section.section)}
                  className={`text-left rounded-lg border p-4 transition-all hover:shadow-sm ${
                    selectedSection === section.section
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 bg-white hover:border-primary-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-gray-900">{section.section}</span>
                    {getTrendIcon(section.trend)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1 truncate">{section.name}</div>
                  <div className="mt-2 text-sm">
                    <span className="font-semibold text-gray-700">{section.total_patents.toLocaleString()}</span>
                    <span className="text-gray-500 ml-1">patents</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {section.market_share}% share | {section.momentum.toFixed(1)}x momentum
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Cross-Domain Opportunities */}
        {selectedSection && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Target className="h-5 w-5 text-gray-400" />
              Cross-Domain Opportunities for Section {selectedSection}
            </h2>

            {crossDomainQuery.isLoading && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Finding opportunities...
              </div>
            )}

            {crossDomainQuery.data && crossDomainQuery.data.opportunities.length > 0 && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {crossDomainQuery.data.opportunities.map((opp) => (
                  <div
                    key={opp.cpc_code}
                    className="rounded-lg border border-gray-200 bg-white p-4 hover:border-primary-200"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm font-semibold text-gray-900">{opp.cpc_code}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          opp.status === 'untapped'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {opp.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{opp.section_name}</div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500">Patents:</span>
                        <span className="ml-1 font-medium">{opp.patent_count.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Avg Citations:</span>
                        <span className="ml-1 font-medium">{opp.avg_citations}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Existing Combos:</span>
                        <span className="ml-1 font-medium">{opp.existing_combinations}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Score:</span>
                        <span className="ml-1 font-semibold text-primary-600">
                          {(opp.opportunity_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {crossDomainQuery.data && crossDomainQuery.data.opportunities.length === 0 && (
              <div className="mt-4 text-sm text-gray-500">
                No cross-domain opportunities found for this section.
              </div>
            )}
          </div>
        )}

        {/* White Space Gaps */}
        <div className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-gray-400" />
              Technology Gaps
            </h2>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={cpcPrefix}
                onChange={(e) => setCpcPrefix(e.target.value)}
                placeholder="Filter by CPC..."
                className="w-32 rounded-md border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Areas with declining activity but strong historical foundations
          </p>

          {gapsQuery.isLoading && (
            <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Discovering gaps...
            </div>
          )}

          {gapsQuery.error && (
            <div className="mt-4 flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              Failed to load white spaces
            </div>
          )}

          {gapsQuery.data && (
            <>
              <div className="mt-2 text-xs text-gray-500">
                Found {gapsQuery.data.total_found} opportunities
              </div>
              <div className="mt-4 space-y-3">
                {gapsQuery.data.white_spaces.map((ws) => (
                  <div
                    key={ws.cpc_code}
                    className="rounded-lg border border-gray-200 bg-white p-4 hover:border-primary-200 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-gray-900">
                            {ws.cpc_code}
                          </span>
                          {getOpportunityBadge(ws.opportunity_type)}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">{ws.section_name}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-primary-600">
                          {(ws.gap_score * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-gray-500">gap score</div>
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-4 gap-4 text-xs">
                      <div>
                        <div className="text-gray-500">Historical</div>
                        <div className="font-semibold text-gray-700">{ws.historical_patents}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Recent</div>
                        <div className="font-semibold text-gray-700">{ws.recent_patents}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Decline</div>
                        <div className="font-semibold text-red-600">
                          {(ws.decline_ratio * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500">High Impact</div>
                        <div className="font-semibold text-gray-700">{ws.high_impact_count}</div>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs">
                      <span className="text-gray-500">
                        Max citations: {ws.max_citations}
                      </span>
                      <Link
                        to={`/ideas?cpc=${ws.cpc_code}`}
                        className="flex items-center gap-1 text-primary-600 hover:text-primary-700"
                      >
                        Generate ideas
                        <ChevronRight className="h-3 w-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default WhiteSpacePage

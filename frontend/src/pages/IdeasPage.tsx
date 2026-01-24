import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Zap,
  Lightbulb,
  Sparkles,
  Loader2,
  Tag,
  Target,
} from 'lucide-react'
import { api } from '../lib/api'

interface GeneratedIdea {
  title: string
  description: string
  rationale: string
  target_cpc: string
  inspired_by: string[]
  novelty_score: number
}

interface IdeaResponse {
  ideas: GeneratedIdea[]
  focus: string
  cpc_prefix: string | null
  seed_patents_used: number
  trends_used: number
}

interface SeedPatent {
  patent_number: string
  title: string
  abstract: string
  cpc_codes: string[]
  expiration_date: string | null
  cited_by_count: number
  assignee: string | null
}

interface GrowthArea {
  cpc_code: string
  patent_count: number
}

interface SeedResponse {
  expiring_patents: SeedPatent[]
  growth_areas: GrowthArea[]
}

type FocusMode = 'expiring' | 'combination' | 'improvement'

function IdeasPage() {
  const [cpcPrefix, setCpcPrefix] = useState('')
  const [focus, setFocus] = useState<FocusMode>('expiring')
  const [count, setCount] = useState(5)
  const [contextText, setContextText] = useState('')

  const seedsQuery = useQuery<SeedResponse>({
    queryKey: ['idea-seeds', cpcPrefix],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (cpcPrefix) params.cpc_prefix = cpcPrefix
      const resp = await api.get('/ideas/seeds', { params })
      return resp.data
    },
  })

  const generateMutation = useMutation<IdeaResponse>({
    mutationFn: async () => {
      const params: Record<string, string | number> = { focus, count }
      if (cpcPrefix) params.cpc_prefix = cpcPrefix
      if (contextText) params.context_text = contextText
      const resp = await api.post('/ideas/generate', null, { params })
      return resp.data
    },
  })

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    generateMutation.mutate()
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
                <Link to="/trends" className="text-sm font-medium text-gray-600 hover:text-gray-900">Trends</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <Sparkles className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-gray-900">AI Idea Generation</h1>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          Generate novel invention ideas using AI analysis of expiring patents, technology trends, and cross-domain combinations.
        </p>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Controls */}
          <div className="lg:col-span-1 space-y-4">
            <form onSubmit={handleGenerate} className="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
              <h2 className="text-sm font-semibold text-gray-900">Generation Settings</h2>

              {/* Focus Mode */}
              <div>
                <label className="text-xs font-medium text-gray-600">Strategy</label>
                <div className="mt-1 space-y-1">
                  {([
                    { value: 'expiring', label: 'Expiring Patents', desc: 'Ideas from soon-to-expire technologies' },
                    { value: 'combination', label: 'Cross-Domain', desc: 'Combine different tech areas' },
                    { value: 'improvement', label: 'Improvements', desc: 'Enhance high-impact patents' },
                  ] as const).map((opt) => (
                    <label
                      key={opt.value}
                      className={`flex items-start gap-2 rounded-md p-2 cursor-pointer transition-colors ${
                        focus === opt.value ? 'bg-primary-50 border border-primary-200' : 'hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="focus"
                        value={opt.value}
                        checked={focus === opt.value}
                        onChange={() => setFocus(opt.value)}
                        className="mt-0.5"
                      />
                      <div>
                        <div className="text-sm font-medium text-gray-800">{opt.label}</div>
                        <div className="text-xs text-gray-500">{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* CPC Prefix */}
              <div>
                <label className="text-xs font-medium text-gray-600">Technology Area (CPC)</label>
                <input
                  type="text"
                  value={cpcPrefix}
                  onChange={(e) => setCpcPrefix(e.target.value)}
                  placeholder="e.g., H01L, G06N"
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              {/* Count */}
              <div>
                <label className="text-xs font-medium text-gray-600">Number of Ideas</label>
                <select
                  value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value={3}>3 ideas</option>
                  <option value={5}>5 ideas</option>
                  <option value={8}>8 ideas</option>
                  <option value={10}>10 ideas</option>
                </select>
              </div>

              {/* Context */}
              <div>
                <label className="text-xs font-medium text-gray-600">Additional Context (optional)</label>
                <textarea
                  value={contextText}
                  onChange={(e) => setContextText(e.target.value)}
                  placeholder="Describe specific problems or domains to focus on..."
                  rows={3}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              <button
                type="submit"
                disabled={generateMutation.isPending}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Ideas
                  </>
                )}
              </button>
            </form>

            {/* Seed Data Preview */}
            {seedsQuery.data && (
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Available Seeds</h3>
                <div className="mt-2 space-y-2 text-sm">
                  <div className="flex justify-between text-gray-600">
                    <span>Expiring patents:</span>
                    <span className="font-medium">{seedsQuery.data.expiring_patents.length}</span>
                  </div>
                  <div className="flex justify-between text-gray-600">
                    <span>Growth areas:</span>
                    <span className="font-medium">{seedsQuery.data.growth_areas.length}</span>
                  </div>
                  {seedsQuery.data.growth_areas.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {seedsQuery.data.growth_areas.slice(0, 5).map((g) => (
                        <span key={g.cpc_code} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                          {g.cpc_code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right: Results */}
          <div className="lg:col-span-2">
            {generateMutation.isPending && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
                <p className="mt-4 text-sm text-gray-600">Analyzing patent landscape and generating ideas...</p>
              </div>
            )}

            {generateMutation.isError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                Failed to generate ideas. Please try again.
              </div>
            )}

            {generateMutation.data && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    Generated <span className="font-medium">{generateMutation.data.ideas.length}</span> ideas
                    {generateMutation.data.seed_patents_used > 0 && (
                      <span> from {generateMutation.data.seed_patents_used} seed patents</span>
                    )}
                  </p>
                  <span className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700">
                    {generateMutation.data.focus}
                  </span>
                </div>

                {generateMutation.data.ideas.map((idea, i) => (
                  <IdeaCard key={i} idea={idea} index={i + 1} />
                ))}
              </div>
            )}

            {!generateMutation.data && !generateMutation.isPending && (
              <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
                <Lightbulb className="mx-auto h-12 w-12 text-gray-300" />
                <h3 className="mt-4 text-sm font-medium text-gray-900">Generate Invention Ideas</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Configure your parameters and click Generate to discover novel invention opportunities
                  powered by AI analysis of the patent landscape.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function IdeaCard({ idea, index }: { idea: GeneratedIdea; index: number }) {
  const noveltyColor = idea.novelty_score >= 0.8
    ? 'text-green-700 bg-green-50 border-green-200'
    : idea.novelty_score >= 0.6
      ? 'text-blue-700 bg-blue-50 border-blue-200'
      : 'text-gray-700 bg-gray-50 border-gray-200'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-primary-200 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
              {index}
            </span>
            <h3 className="text-base font-semibold text-gray-900">{idea.title}</h3>
          </div>
          <p className="mt-2 text-sm text-gray-700">{idea.description}</p>
          <div className="mt-3 rounded-md bg-gray-50 p-3">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Rationale</p>
            <p className="mt-1 text-sm text-gray-600">{idea.rationale}</p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            {idea.target_cpc && (
              <span className="flex items-center gap-1">
                <Tag className="h-3 w-3" />
                {idea.target_cpc}
              </span>
            )}
            {idea.inspired_by.length > 0 && (
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                Inspired by: {idea.inspired_by.join(', ')}
              </span>
            )}
          </div>
        </div>
        <div className={`rounded-lg border px-3 py-2 text-center shrink-0 ${noveltyColor}`}>
          <div className="text-[10px] font-medium uppercase">Novelty</div>
          <div className="text-lg font-bold">{(idea.novelty_score * 100).toFixed(0)}%</div>
        </div>
      </div>
    </div>
  )
}

export default IdeasPage

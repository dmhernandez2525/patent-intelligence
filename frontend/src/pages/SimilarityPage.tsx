import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  Zap,
  Search,
  GitBranch,
  Building,
  Calendar,
  Tag,
  Loader2,
  Layers,
} from 'lucide-react'
import { api } from '../lib/api'

interface SimilarPatent {
  patent_number: string
  title: string
  abstract: string | null
  filing_date: string | null
  grant_date: string | null
  assignee_organization: string | null
  cpc_codes: string[] | null
  country: string
  status: string
  citation_count: number | null
  similarity_score: number
  source: string | null
}

interface SimilarityResponse {
  results: SimilarPatent[]
  query_patent: string | null
  query_text: string | null
  total_found: number
}

interface PriorArtResponse {
  target_patent: string | null
  target_filing_date: string | null
  prior_art: SimilarPatent[]
  total_found: number
  semantic_count: number
  citation_count: number
}

type SearchMode = 'similar' | 'prior-art'

function SimilarityPage() {
  const [mode, setMode] = useState<SearchMode>('similar')
  const [patentNumber, setPatentNumber] = useState('')
  const [textQuery, setTextQuery] = useState('')
  const [inputType, setInputType] = useState<'patent' | 'text'>('text')
  const [topK, setTopK] = useState(20)
  const [minScore, setMinScore] = useState(0.5)
  const [excludeSameAssignee, setExcludeSameAssignee] = useState(false)

  const similarMutation = useMutation<SimilarityResponse>({
    mutationFn: async () => {
      const resp = await api.post('/similarity/similar', {
        patent_number: inputType === 'patent' ? patentNumber : undefined,
        text_query: inputType === 'text' ? textQuery : undefined,
        top_k: topK,
        min_score: minScore,
        exclude_same_assignee: excludeSameAssignee,
      })
      return resp.data
    },
  })

  const priorArtMutation = useMutation<PriorArtResponse>({
    mutationFn: async () => {
      const resp = await api.post('/similarity/prior-art', {
        patent_number: inputType === 'patent' ? patentNumber : undefined,
        text_query: inputType === 'text' ? textQuery : undefined,
        top_k: topK,
        min_score: minScore,
      })
      return resp.data
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputType === 'patent' && !patentNumber.trim()) return
    if (inputType === 'text' && !textQuery.trim()) return

    if (mode === 'similar') {
      similarMutation.mutate()
    } else {
      priorArtMutation.mutate()
    }
  }

  const isLoading = similarMutation.isPending || priorArtMutation.isPending
  const results = mode === 'similar' ? similarMutation.data?.results : priorArtMutation.data?.prior_art

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
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Patent Similarity & Prior Art</h1>
        <p className="mt-1 text-sm text-gray-600">
          Find similar patents using AI embeddings or discover prior art for patentability analysis.
        </p>

        {/* Mode Selector */}
        <div className="mt-6 flex gap-2">
          <button
            onClick={() => setMode('similar')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              mode === 'similar'
                ? 'bg-primary-100 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            <Layers className="h-4 w-4" />
            Find Similar Patents
          </button>
          <button
            onClick={() => setMode('prior-art')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              mode === 'prior-art'
                ? 'bg-primary-100 text-primary-700 border border-primary-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            <GitBranch className="h-4 w-4" />
            Prior Art Search
          </button>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mt-4 rounded-lg border border-gray-200 bg-white p-5">
          {/* Input Type Toggle */}
          <div className="flex items-center gap-4 mb-4">
            <span className="text-sm font-medium text-gray-700">Search by:</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setInputType('text')}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  inputType === 'text'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Text / Concept
              </button>
              <button
                type="button"
                onClick={() => setInputType('patent')}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  inputType === 'patent'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Patent Number
              </button>
            </div>
          </div>

          {/* Input Field */}
          <div className="flex gap-3">
            {inputType === 'text' ? (
              <textarea
                value={textQuery}
                onChange={(e) => setTextQuery(e.target.value)}
                placeholder={mode === 'similar'
                  ? "Describe the technology or invention concept..."
                  : "Describe the invention to check for prior art..."
                }
                rows={3}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              />
            ) : (
              <input
                type="text"
                value={patentNumber}
                onChange={(e) => setPatentNumber(e.target.value)}
                placeholder="Enter patent number (e.g., US-10123456-B2)"
                className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              />
            )}
            <button
              type="submit"
              disabled={isLoading}
              className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white hover:bg-primary-700 transition-colors disabled:opacity-50 self-end"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Search className="h-5 w-5" />
              )}
            </button>
          </div>

          {/* Options */}
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            <label className="flex items-center gap-2 text-gray-600">
              <span>Top results:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="rounded border border-gray-300 px-2 py-1 text-xs"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-gray-600">
              <span>Min score:</span>
              <select
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="rounded border border-gray-300 px-2 py-1 text-xs"
              >
                <option value={0.3}>0.3 (Broad)</option>
                <option value={0.5}>0.5 (Default)</option>
                <option value={0.7}>0.7 (Strict)</option>
                <option value={0.8}>0.8 (Very strict)</option>
              </select>
            </label>
            {mode === 'similar' && (
              <label className="flex items-center gap-2 text-gray-600">
                <input
                  type="checkbox"
                  checked={excludeSameAssignee}
                  onChange={(e) => setExcludeSameAssignee(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span>Exclude same assignee</span>
              </label>
            )}
          </div>
        </form>

        {/* Prior Art Stats */}
        {mode === 'prior-art' && priorArtMutation.data && (
          <div className="mt-4 flex gap-4">
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm">
              <span className="text-gray-500">Total found:</span>{' '}
              <span className="font-medium">{priorArtMutation.data.total_found}</span>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm">
              <span className="text-gray-500">Semantic matches:</span>{' '}
              <span className="font-medium">{priorArtMutation.data.semantic_count}</span>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm">
              <span className="text-gray-500">Citation matches:</span>{' '}
              <span className="font-medium">{priorArtMutation.data.citation_count}</span>
            </div>
          </div>
        )}

        {/* Results */}
        <div className="mt-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          )}

          {(similarMutation.isError || priorArtMutation.isError) && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              Search failed. Ensure embeddings have been generated for the patent database.
            </div>
          )}

          {results && results.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Found <span className="font-medium">{results.length}</span>{' '}
                {mode === 'similar' ? 'similar patents' : 'prior art candidates'}
              </p>
              {results.map((patent) => (
                <SimilarPatentCard key={patent.patent_number} patent={patent} mode={mode} />
              ))}
            </div>
          )}

          {results && results.length === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <Layers className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-4 text-sm font-medium text-gray-900">No results found</h3>
              <p className="mt-2 text-sm text-gray-500">
                Try lowering the minimum similarity score or broadening your query.
              </p>
            </div>
          )}

          {!results && !isLoading && (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-4 text-sm font-medium text-gray-900">
                {mode === 'similar' ? 'Find Similar Patents' : 'Search Prior Art'}
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                {mode === 'similar'
                  ? 'Enter a patent number or describe a technology to find semantically similar patents.'
                  : 'Enter a patent number or describe an invention to find potential prior art.'}
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function SimilarPatentCard({ patent, mode }: { patent: SimilarPatent; mode: SearchMode }) {
  const scoreColor = patent.similarity_score >= 0.8
    ? 'text-red-600 bg-red-50 border-red-200'
    : patent.similarity_score >= 0.6
      ? 'text-orange-600 bg-orange-50 border-orange-200'
      : 'text-green-600 bg-green-50 border-green-200'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-primary-200 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-mono text-primary-600">{patent.patent_number}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              patent.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {patent.status}
            </span>
            {patent.source && (
              <span className="rounded-full px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-600">
                {patent.source}
              </span>
            )}
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
            {patent.filing_date && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Filed: {patent.filing_date}
              </span>
            )}
            {patent.cpc_codes && patent.cpc_codes.length > 0 && (
              <span className="flex items-center gap-1">
                <Tag className="h-3 w-3" />
                {patent.cpc_codes.slice(0, 3).join(', ')}
              </span>
            )}
          </div>
        </div>
        <div className={`ml-4 rounded-lg border px-3 py-2 text-center ${scoreColor}`}>
          <div className="text-xs font-medium">
            {mode === 'prior-art' ? 'Relevance' : 'Similarity'}
          </div>
          <div className="text-lg font-bold">
            {(patent.similarity_score * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </div>
  )
}

export default SimilarityPage

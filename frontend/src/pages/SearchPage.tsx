import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, Zap, Filter, Calendar, Building, Tag, ChevronLeft, ChevronRight } from 'lucide-react'
import { api, type SearchResponse, type SearchResult } from '../lib/api'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'hybrid' | 'fulltext' | 'semantic'>('hybrid')
  const [country, setCountry] = useState('')
  const [status, setStatus] = useState('')
  const [cpcFilter, setCpcFilter] = useState('')
  const [assignee, setAssignee] = useState('')
  const [page, setPage] = useState(1)
  const [submittedQuery, setSubmittedQuery] = useState('')

  const { data: searchResults, isLoading, isError } = useQuery<SearchResponse>({
    queryKey: ['search', submittedQuery, searchType, country, status, cpcFilter, assignee, page],
    queryFn: async () => {
      const resp = await api.post('/search', {
        query: submittedQuery,
        search_type: searchType,
        country: country || undefined,
        status: status || undefined,
        cpc_codes: cpcFilter ? [cpcFilter] : undefined,
        assignee: assignee || undefined,
        page,
        per_page: 20,
      })
      return resp.data
    },
    enabled: submittedQuery.length > 0,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      setPage(1)
      setSubmittedQuery(query.trim())
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
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
                <Link to="/ingestion" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ingestion</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Patent Search</h1>
        <p className="mt-1 text-sm text-gray-600">Search 200M+ patents using AI-powered semantic or traditional keyword search.</p>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="mt-6">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search patents by keyword, concept, or patent number..."
                className="w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-4 text-sm placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              Search
            </button>
          </div>

          {/* Search Type */}
          <div className="mt-3 flex items-center gap-4">
            <span className="text-xs font-medium text-gray-500 uppercase">Search Mode:</span>
            <div className="flex gap-2">
              {(['hybrid', 'semantic', 'fulltext'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSearchType(type)}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    searchType === type
                      ? 'bg-primary-100 text-primary-700'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </form>

        {/* Filters */}
        <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All Countries</option>
              <option value="US">United States</option>
              <option value="EP">Europe (EPO)</option>
              <option value="JP">Japan</option>
              <option value="CN">China</option>
              <option value="KR">South Korea</option>
            </select>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="lapsed">Lapsed</option>
            </select>
            <input
              type="text"
              value={cpcFilter}
              onChange={(e) => setCpcFilter(e.target.value)}
              placeholder="CPC Code (e.g., H01L)"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
            />
            <input
              type="text"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              placeholder="Assignee"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
            />
          </div>
        </div>

        {/* Results */}
        <div className="mt-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          )}

          {isError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              Search failed. Please try again.
            </div>
          )}

          {searchResults && searchResults.total > 0 && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {((page - 1) * 20) + 1}-{Math.min(page * 20, searchResults.total)} of{' '}
                  <span className="font-medium">{searchResults.total.toLocaleString()}</span> results
                  {' '}for "<span className="font-medium">{searchResults.query}</span>"
                  {' '}({searchResults.search_type} search)
                </p>
              </div>

              <div className="mt-4 space-y-4">
                {searchResults.results.map((result) => (
                  <SearchResultCard key={result.patent_number} result={result} />
                ))}
              </div>

              {/* Pagination */}
              {searchResults.total > 20 && (
                <div className="mt-6 flex items-center justify-center gap-4">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
                  >
                    <ChevronLeft className="h-4 w-4" /> Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page} of {Math.ceil(searchResults.total / 20)}
                  </span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page * 20 >= searchResults.total}
                    className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
                  >
                    Next <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </>
          )}

          {searchResults && searchResults.total === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-4 text-sm font-medium text-gray-900">No results found</h3>
              <p className="mt-2 text-sm text-gray-500">
                Try adjusting your search terms or filters.
              </p>
            </div>
          )}

          {!submittedQuery && (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <Search className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-4 text-sm font-medium text-gray-900">Search patents</h3>
              <p className="mt-2 text-sm text-gray-500">
                Enter a search query to find patents. Try searching for a technology, company, or patent number.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function SearchResultCard({ result }: { result: SearchResult }) {
  const statusColor = {
    active: 'bg-green-100 text-green-700',
    expired: 'bg-red-100 text-red-700',
    lapsed: 'bg-yellow-100 text-yellow-700',
  }[result.status] || 'bg-gray-100 text-gray-700'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-primary-200 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-primary-600">{result.patent_number}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor}`}>
              {result.status}
            </span>
            <span className="text-xs text-gray-400">{result.country}</span>
          </div>
          <h3 className="mt-1 text-base font-semibold text-gray-900 line-clamp-2">
            {result.title}
          </h3>
          {result.abstract && (
            <p className="mt-2 text-sm text-gray-600 line-clamp-3">{result.abstract}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
            {result.assignee_organization && (
              <span className="flex items-center gap-1">
                <Building className="h-3 w-3" />
                {result.assignee_organization}
              </span>
            )}
            {result.filing_date && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Filed: {result.filing_date}
              </span>
            )}
            {result.cpc_codes && result.cpc_codes.length > 0 && (
              <span className="flex items-center gap-1">
                <Tag className="h-3 w-3" />
                {result.cpc_codes.slice(0, 3).join(', ')}
                {result.cpc_codes.length > 3 && ` +${result.cpc_codes.length - 3}`}
              </span>
            )}
          </div>
        </div>
        <div className="ml-4 text-right">
          <div className="text-xs text-gray-500">Relevance</div>
          <div className="text-sm font-bold text-primary-600">
            {(result.relevance_score * 100).toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  )
}

export default SearchPage

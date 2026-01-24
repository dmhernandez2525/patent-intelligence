import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Zap, Filter } from 'lucide-react'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'hybrid' | 'fulltext' | 'semantic'>('hybrid')

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
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Patent Search</h1>
        <p className="mt-1 text-sm text-gray-600">Search 200M+ patents using AI-powered semantic or traditional keyword search.</p>

        {/* Search Bar */}
        <div className="mt-6">
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
            <button className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white hover:bg-primary-700 transition-colors">
              Search
            </button>
          </div>

          {/* Search Type Selector */}
          <div className="mt-3 flex items-center gap-4">
            <span className="text-xs font-medium text-gray-500 uppercase">Search Mode:</span>
            <div className="flex gap-2">
              {(['hybrid', 'semantic', 'fulltext'] as const).map((type) => (
                <button
                  key={type}
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
        </div>

        {/* Filters Panel */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
            <select className="rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="">All Countries</option>
              <option value="US">United States</option>
              <option value="EP">Europe (EPO)</option>
              <option value="JP">Japan</option>
              <option value="CN">China</option>
              <option value="KR">South Korea</option>
            </select>
            <select className="rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="lapsed">Lapsed</option>
            </select>
            <input
              type="text"
              placeholder="CPC Code (e.g., H01L)"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
            />
            <input
              type="text"
              placeholder="Assignee"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400"
            />
          </div>
        </div>

        {/* Results Area */}
        <div className="mt-8">
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
            <Search className="mx-auto h-12 w-12 text-gray-300" />
            <h3 className="mt-4 text-sm font-medium text-gray-900">No search results</h3>
            <p className="mt-2 text-sm text-gray-500">
              Enter a search query to find patents. Try searching for a technology, company, or patent number.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default SearchPage

import { Link, useLocation } from 'react-router-dom'
import { Zap, Home } from 'lucide-react'

interface DemoLayoutProps {
  children: React.ReactNode
  title: string
  description: string
  alertCount?: number
}

export function DemoLayout({ children, title, description, alertCount }: DemoLayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/demo', label: 'Dashboard' },
    { path: '/demo/search', label: 'Search' },
    { path: '/demo/expiration', label: 'Expiration' },
    { path: '/demo/similarity', label: 'Similarity' },
    { path: '/demo/trends', label: 'Trends' },
    { path: '/demo/whitespace', label: 'White Space' },
    { path: '/demo/ideas', label: 'Ideas' },
    { path: '/demo/watchlist', label: 'Watchlist', badge: alertCount },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Demo Banner */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-center py-2 px-4">
        <div className="flex items-center justify-center gap-4">
          <span className="text-sm font-medium">
            Demo Mode - Exploring with sample data
          </span>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs bg-white/20 hover:bg-white/30 rounded-full px-3 py-1 transition-colors"
          >
            <Home className="h-3 w-3" />
            Exit Demo
          </Link>
        </div>
      </div>

      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-6">
              <Link to="/demo" className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-primary-600 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-bold text-gray-900">Patent Intelligence</span>
                <span className="ml-1 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                  Demo
                </span>
              </Link>
              <nav className="hidden md:flex items-center gap-4">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`text-sm font-medium transition-colors flex items-center gap-1 ${
                      location.pathname === item.path
                        ? 'text-primary-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {item.label}
                    {item.badge ? (
                      <span className="bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                        {item.badge}
                      </span>
                    ) : null}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
        {children}
      </main>
    </div>
  )
}

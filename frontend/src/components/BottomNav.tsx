import { Link, useLocation } from 'react-router-dom'
import { Search, LayoutDashboard, Clock, Lightbulb, Map } from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/search', label: 'Search', icon: Search },
  { path: '/expiration', label: 'Expiring', icon: Clock },
  { path: '/whitespace', label: 'White Space', icon: Map },
  { path: '/ideas', label: 'Ideas', icon: Lightbulb },
]

function BottomNav() {
  const location = useLocation()

  // Hide on Landing page
  if (location.pathname === '/') return null

  const isActive = (path: string) => location.pathname === path

  return (
    <nav className="bottom-nav fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white/95 backdrop-blur-sm sm:hidden">
      <div className="flex items-center justify-around px-1 pb-safe">
        {navItems.map(({ path, label, icon: Icon }) => {
          const active = isActive(path)
          return (
            <Link
              key={path}
              to={path}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition-colors ${
                active
                  ? 'text-primary-600'
                  : 'text-gray-500 active:text-gray-700'
              }`}
            >
              <Icon className={`h-5 w-5 ${active ? 'text-primary-600' : 'text-gray-400'}`} />
              <span>{label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export default BottomNav

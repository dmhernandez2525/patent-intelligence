import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import SearchPage from './pages/SearchPage'
import ExpirationPage from './pages/ExpirationPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/expiration" element={<ExpirationPage />} />
    </Routes>
  )
}

export default App

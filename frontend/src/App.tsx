import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import SearchPage from './pages/SearchPage'
import ExpirationPage from './pages/ExpirationPage'
import SimilarityPage from './pages/SimilarityPage'
import TrendsPage from './pages/TrendsPage'
import IngestionPage from './pages/IngestionPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/expiration" element={<ExpirationPage />} />
      <Route path="/similarity" element={<SimilarityPage />} />
      <Route path="/trends" element={<TrendsPage />} />
      <Route path="/ingestion" element={<IngestionPage />} />
    </Routes>
  )
}

export default App

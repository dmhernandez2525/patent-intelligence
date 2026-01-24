import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Zap, Database, Play, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface IngestionJob {
  id: number
  source: string
  status: string
  job_type: string
  total_fetched: number
  total_inserted: number
  total_updated: number
  total_errors: number
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  error_message: string | null
  celery_task_id: string | null
  created_at: string | null
}

interface IngestionStatus {
  jobs: IngestionJob[]
  total_jobs: number
  active_jobs: number
  last_successful: IngestionJob | null
  checkpoint: { source: string; last_sync_date: string | null; total_patents_ingested: number } | null
}

function IngestionPage() {
  const [source, setSource] = useState<'uspto' | 'epo'>('uspto')
  const [batchSize, setBatchSize] = useState(100)
  const [maxPatents, setMaxPatents] = useState(1000)
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery<IngestionStatus>({
    queryKey: ['ingestion-status', source],
    queryFn: async () => {
      const resp = await api.get(`/ingestion/status?source=${source}`)
      return resp.data
    },
    refetchInterval: 5000,
  })

  const triggerMutation = useMutation({
    mutationFn: async () => {
      const resp = await api.post('/ingestion/trigger', {
        source,
        batch_size: batchSize,
        max_patents: maxPatents,
      })
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestion-status'] })
    },
  })

  const statusIcon = (jobStatus: string) => {
    switch (jobStatus) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running': return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />
      default: return <Clock className="h-4 w-4 text-gray-400" />
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
                <Link to="/search" className="text-sm font-medium text-gray-600 hover:text-gray-900">Search</Link>
                <Link to="/expiration" className="text-sm font-medium text-gray-600 hover:text-gray-900">Expiration</Link>
                <Link to="/trends" className="text-sm font-medium text-gray-600 hover:text-gray-900">Trends</Link>
                <Link to="/ideas" className="text-sm font-medium text-gray-600 hover:text-gray-900">Ideas</Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Ingestion</h1>
            <p className="mt-1 text-sm text-gray-600">
              Manage patent data ingestion from USPTO PatentsView and EPO Open Patent Services.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary-600" />
            <span className="text-sm font-medium text-gray-700">
              {status?.checkpoint?.total_patents_ingested ?? 0} patents ingested
            </span>
          </div>
        </div>

        {/* Trigger Controls */}
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">Trigger Ingestion</h2>
          <p className="mt-1 text-sm text-gray-600">
            Start a new patent data ingestion job from the selected data source.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Data Source</label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value as 'uspto' | 'epo')}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="uspto">USPTO (United States)</option>
                <option value="epo">EPO (Europe, 90+ countries)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Batch Size</label>
              <input
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                min={10}
                max={1000}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Patents</label>
              <input
                type="number"
                value={maxPatents}
                onChange={(e) => setMaxPatents(Number(e.target.value))}
                min={1}
                max={100000}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={() => triggerMutation.mutate()}
                disabled={triggerMutation.isPending || (status?.active_jobs ?? 0) > 0}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {triggerMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Start Ingestion
              </button>
            </div>
          </div>
          {triggerMutation.isError && (
            <p className="mt-3 text-sm text-red-600">
              Failed to trigger ingestion. A job may already be running.
            </p>
          )}
        </div>

        {/* Active Jobs */}
        {(status?.active_jobs ?? 0) > 0 && (
          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
              <span className="font-medium text-blue-800">Ingestion in progress...</span>
            </div>
          </div>
        )}

        {/* Job History */}
        <div className="mt-6">
          <h2 className="text-lg font-semibold text-gray-900">Job History</h2>
          {isLoading ? (
            <div className="mt-4 flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : (status?.jobs?.length ?? 0) === 0 ? (
            <div className="mt-4 rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
              <Database className="mx-auto h-10 w-10 text-gray-300" />
              <p className="mt-3 text-sm text-gray-500">No ingestion jobs yet. Start one above.</p>
            </div>
          ) : (
            <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 bg-white">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fetched</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Inserted</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Errors</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {status?.jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {statusIcon(job.status)}
                          <span className="text-sm capitalize">{job.status}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 uppercase">{job.source}</td>
                      <td className="px-4 py-3 text-sm text-gray-700 capitalize">{job.job_type}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 font-medium">{job.total_fetched.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm text-green-600">{job.total_inserted.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm text-red-600">{job.total_errors}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : '--'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {job.started_at ? new Date(job.started_at).toLocaleString() : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default IngestionPage

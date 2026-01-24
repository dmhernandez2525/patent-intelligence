import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Patent {
  id: number
  patent_number: string
  title: string
  abstract: string | null
  filing_date: string | null
  grant_date: string | null
  expiration_date: string | null
  assignee: string | null
  assignee_organization: string | null
  inventors: string[] | null
  cpc_codes: string[] | null
  status: string
  country: string
  citation_count: number
  cited_by_count: number
  claim_count: number
}

export interface SearchResult {
  patent_number: string
  title: string
  abstract: string | null
  filing_date: string | null
  grant_date: string | null
  expiration_date: string | null
  assignee_organization: string | null
  inventors: string[] | null
  cpc_codes: string[] | null
  status: string
  country: string
  citation_count: number | null
  relevance_score: number
}

export interface PatentListResponse {
  patents: Patent[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
  search_type: string
  page: number
  per_page: number
}

export async function searchPatents(params: {
  query: string
  search_type?: string
  page?: number
  per_page?: number
}): Promise<SearchResponse> {
  const response = await api.post('/search', params)
  return response.data
}

export async function getPatents(params?: {
  page?: number
  per_page?: number
  country?: string
  status?: string
}): Promise<PatentListResponse> {
  const response = await api.get('/patents', { params })
  return response.data
}

export async function getPatentStats(): Promise<{
  total_patents: number
  active: number
  expired: number
  lapsed: number
  countries: number
}> {
  const response = await api.get('/patents/stats/overview')
  return response.data
}

export async function getHealthStatus(): Promise<{
  status: string
  version: string
  service: string
}> {
  const response = await api.get('/health')
  return response.data
}

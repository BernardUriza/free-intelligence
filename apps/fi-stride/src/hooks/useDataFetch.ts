import { useState, useEffect } from 'react'

export interface UseDataFetchOptions<_T> {
  url: string
  headers?: Record<string, string>
  dependencies?: Array<string | number | boolean>
}

export interface UseDataFetchResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Custom hook for fetching data with loading and error states.
 * Eliminates boilerplate code from pages.
 *
 * @example
 * const { data, loading, error } = useDataFetch<Consultation[]>({
 *   url: '/api/consultations',
 *   headers: { Authorization: `Bearer ${token}` }
 * })
 */
export function useDataFetch<T = unknown>({
  url,
  headers,
  dependencies = []
}: UseDataFetchOptions<T>): UseDataFetchResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...headers
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data'
      setError(errorMessage)
      console.error(`useDataFetch error (${url}):`, err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [url, ...dependencies])

  return { data, loading, error, refetch: fetchData }
}

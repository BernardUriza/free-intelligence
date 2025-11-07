import { ApiErrorClass } from '../types/api'

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  headers?: Record<string, string>
  body?: unknown
  timeout?: number
}

/**
 * Centralized API client for FI-Stride PWA
 * Handles authentication, error handling, logging, and retries
 */
class ApiClient {
  private baseUrl: string
  private defaultTimeout: number = 10000

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl
  }

  /**
   * Get authorization token from localStorage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('fi-stride-auth-token')
  }

  /**
   * Build authorization header if token exists
   */
  private getAuthHeaders(): Record<string, string> {
    const token = this.getAuthToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  /**
   * Execute fetch with timeout
   */
  private async fetchWithTimeout(
    url: string,
    options: RequestInit,
    timeout: number
  ): Promise<Response> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      })
      return response
    } finally {
      clearTimeout(timeoutId)
    }
  }

  /**
   * Generic request method
   */
  async request<T = unknown>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const {
      method = 'GET',
      headers = {},
      body,
      timeout = this.defaultTimeout
    } = options

    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...headers
    }

    const fetchOptions: RequestInit = {
      method,
      headers: requestHeaders
    }

    if (body) {
      fetchOptions.body = JSON.stringify(body)
    }

    try {
      const response = await this.fetchWithTimeout(url, fetchOptions, timeout)

      // Handle HTTP errors
      if (!response.ok) {
        let errorData: unknown
        try {
          errorData = await response.json()
        } catch {
          errorData = { detail: response.statusText }
        }

        throw new ApiErrorClass(
          response.status,
          `HTTP ${response.status}`,
          typeof errorData === 'object' ? (errorData as Record<string, unknown>) : undefined
        )
      }

      // Parse successful response
      const data = await response.json()

      // Log successful requests (in development)
      if (process.env.NODE_ENV === 'development') {
        console.log(`[API] ${method} ${endpoint} → ${response.status}`)
      }

      return data as T
    } catch (error) {
      // Handle network errors and timeouts
      if (error instanceof ApiErrorClass) {
        throw error
      }

      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred'

      console.error(`[API Error] ${method} ${endpoint}:`, error)

      throw new ApiErrorClass(
        0,
        `Failed to ${method} ${endpoint}: ${errorMessage}`
      )
    }
  }

  /**
   * GET request helper
   */
  get<T = unknown>(endpoint: string, options?: Omit<RequestOptions, 'method'>) {
    return this.request<T>(endpoint, { ...options, method: 'GET' })
  }

  /**
   * POST request helper
   */
  post<T = unknown>(
    endpoint: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>
  ) {
    return this.request<T>(endpoint, { ...options, method: 'POST', body })
  }

  /**
   * PUT request helper
   */
  put<T = unknown>(
    endpoint: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>
  ) {
    return this.request<T>(endpoint, { ...options, method: 'PUT', body })
  }

  /**
   * DELETE request helper
   */
  delete<T = unknown>(endpoint: string, options?: Omit<RequestOptions, 'method'>) {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' })
  }
}

// Export singleton instance
// In browser environment, import.meta.env is used instead of process.env
const baseUrl = (import.meta.env.VITE_API_URL as string) || ''
export const apiClient = new ApiClient(baseUrl)
export default apiClient

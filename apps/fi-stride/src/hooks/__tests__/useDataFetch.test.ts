import { renderHook, waitFor } from '@testing-library/react'
import { useDataFetch } from '../useDataFetch'

// Mock fetch globally
global.fetch = vi.fn()

interface TestData {
  id: string
  name: string
}

describe('useDataFetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should start with loading true', () => {
    ;(fetch as any).mockImplementationOnce(() =>
      new Promise(() => {
        // Never resolves
      })
    )

    const { result } = renderHook(() =>
      useDataFetch<TestData>({ url: '/api/test' })
    )

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('should fetch data successfully', async () => {
    const mockData = { id: '1', name: 'Test' }
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    })

    const { result } = renderHook(() =>
      useDataFetch<TestData>({ url: '/api/test' })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.error).toBeNull()
  })

  it('should handle HTTP errors', async () => {
    ;(fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Not found' })
    })

    const { result } = renderHook(() =>
      useDataFetch<TestData>({ url: '/api/test' })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeTruthy()
    expect(result.current.error).toContain('HTTP 404')
  })

  it('should handle network errors', async () => {
    ;(fetch as any).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() =>
      useDataFetch<TestData>({ url: '/api/test' })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toContain('Network error')
  })

  it('should include custom headers', async () => {
    const mockData = { id: '1', name: 'Test' }
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    })

    const customHeaders = { Authorization: 'Bearer token' }

    const { result } = renderHook(() =>
      useDataFetch<TestData>({
        url: '/api/test',
        headers: customHeaders
      })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(fetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        headers: expect.objectContaining(customHeaders)
      })
    )
  })

  it('should support manual refetch', async () => {
    const mockData = { id: '1', name: 'Test' }
    ;(fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockData
    })

    const { result } = renderHook(() =>
      useDataFetch<TestData>({ url: '/api/test' })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(fetch).toHaveBeenCalledTimes(1)

    // Manually refetch
    result.current.refetch()

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2)
    })
  })
})

import { useState, useEffect, useCallback } from 'react'
import { invoke, isTauriContext } from '../lib/tauri-adapter'
import { SERVICE_URLS } from '../lib/constants'
import type { TestResult } from '../types/monitor'

export function useLLMTesting(
  ollamaRunning: boolean,
  setActionLoading: (v: string | null) => void,
  setError: (v: string | null) => void,
) {
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [autoTest, setAutoTest] = useState(false)
  const [nextTestIn, setNextTestIn] = useState(60)

  const handleTestOllama = useCallback(async () => {
    if (!ollamaRunning) return
    setActionLoading('test')
    setError(null)

    try {
      let result: TestResult

      if (isTauriContext()) {
        result = await invoke<TestResult>('test_ollama')
      } else {
        const questions = [
          { category: 'math', prompt: 'Cual es la raiz cuadrada de 144? Responde solo el numero.' },
          { category: 'anatomy', prompt: 'Explica brevemente que es el higado y su funcion principal.' },
          { category: 'math', prompt: 'Cual es la raiz cuadrada de 256? Responde solo el numero.' },
          { category: 'anatomy', prompt: 'Explica brevemente que es el corazon y su funcion principal.' },
          { category: 'math', prompt: 'Cual es la raiz cuadrada de 625? Responde solo el numero.' },
          { category: 'anatomy', prompt: 'Explica brevemente que son los pulmones y su funcion.' }
        ]

        const now = Math.floor(Date.now() / 1000)
        const idx = now % questions.length
        const { category, prompt } = questions[idx]

        const start = Date.now()
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 60000)

        const response = await fetch(`${SERVICE_URLS.OLLAMA}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'qwen3:1.7b',
            prompt: prompt,
            stream: false
          }),
          signal: controller.signal
        })

        clearTimeout(timeoutId)
        const elapsed_ms = Date.now() - start

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()

        result = {
          category,
          question: prompt,
          answer: data.response?.trim() || '',
          elapsed_ms,
          timestamp: new Date().toISOString(),
          rag_metadata: null
        }
      }

      setTestResult(result)
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }, [ollamaRunning, setActionLoading, setError])

  const handleTestLLMHealth = useCallback(async () => {
    setActionLoading('smoke-test')
    setError(null)

    try {
      interface SmokeTestResult {
        success: boolean
        latency_ms: number
        response: string
        error?: string
      }

      let result: SmokeTestResult

      if (isTauriContext()) {
        result = await invoke<SmokeTestResult>('test_llm_health')
      } else {
        const start = Date.now()

        try {
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 15000)

          // Pick first available model
          const tagsRes = await fetch(`${SERVICE_URLS.OLLAMA}/api/tags`, { signal: controller.signal })
          const tags = await tagsRes.json()
          const model = tags.models?.[0]?.name || 'qwen3:1.7b'

          const response = await fetch(`${SERVICE_URLS.OLLAMA}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model,
              prompt: 'What is 2+2? Answer with just the number, nothing else.',
              stream: false
            }),
            signal: controller.signal
          })

          clearTimeout(timeoutId)
          const latency_ms = Date.now() - start

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const data = await response.json()
          const answer = data.response?.trim() || ''
          const success = answer.includes('4')

          result = {
            success,
            latency_ms,
            response: answer,
            error: success ? undefined : `Expected '4' in response, got: ${answer}`
          }
        } catch (err: unknown) {
          const latency_ms = Date.now() - start
          const error = err instanceof Error
            ? (err.name === 'AbortError'
              ? 'Request timeout (15s) - Ollama may be loading the model'
              : `HTTP request failed: ${err.message}`)
            : `Unknown error: ${String(err)}`
          result = {
            success: false,
            latency_ms,
            response: '',
            error,
          }
        }
      }

      if (result.success) {
        setTestResult({
          category: 'smoke',
          question: 'What is 2+2?',
          answer: `LLM Health OK\n\nResponse: ${result.response}\nLatency: ${result.latency_ms}ms${isTauriContext() ? '' : ' (browser mode)'}`,
          elapsed_ms: result.latency_ms,
          timestamp: new Date().toISOString(),
          rag_metadata: null
        })
      } else {
        setError(result.error || 'Smoke test failed')
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }, [setActionLoading, setError])

  // Auto-test timer
  useEffect(() => {
    if (!autoTest || !ollamaRunning) {
      setNextTestIn(60)
      return
    }
    const countdown = setInterval(() => {
      setNextTestIn(prev => {
        if (prev <= 1) { handleTestOllama(); return 60 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(countdown)
  }, [autoTest, ollamaRunning, handleTestOllama])

  return {
    testResult,
    autoTest,
    setAutoTest,
    nextTestIn,
    handleTestOllama,
    handleTestLLMHealth,
  }
}

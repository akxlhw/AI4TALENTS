/**
 * useCancellableRequest - React hook for making cancellable API requests
 *
 * Usage:
 *   const { data, loading, error, execute, cancel } = useCancellableRequest(
 *     (signal) => api.talents.list({ ...params }, { signal })
 *   )
 *
 *   useEffect(() => {
 *     execute()
 *     return () => cancel()
 *   }, [dep])
 */
import { useState, useCallback, useRef, useEffect } from 'react'
import { isCancellationError } from '../services/api'

interface UseCancellableRequestResult<T> {
  data: T | null
  loading: boolean
  error: Error | null
  execute: () => Promise<void>
  cancel: () => void
  reset: () => void
}

export function useCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>,
  options?: {
    immediate?: boolean
    onSuccess?: (data: T) => void
    onError?: (error: Error) => void
  }
): UseCancellableRequestResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const controllerRef = useRef<AbortController | null>(null)

  const execute = useCallback(async () => {
    // Cancel any pending request
    if (controllerRef.current) {
      controllerRef.current.abort()
    }

    // Create new controller for this request
    controllerRef.current = new AbortController()
    setLoading(true)
    setError(null)

    try {
      const result = await requestFn(controllerRef.current.signal)
      setData(result)
      options?.onSuccess?.(result)
    } catch (err) {
      // Ignore cancellation errors
      if (!isCancellationError(err)) {
        const error = err instanceof Error ? err : new Error(String(err))
        setError(error)
        options?.onError?.(error)
      }
    } finally {
      setLoading(false)
    }
  }, [requestFn, options])

  const cancel = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort()
      controllerRef.current = null
    }
    setLoading(false)
  }, [])

  const reset = useCallback(() => {
    cancel()
    setData(null)
    setError(null)
    setLoading(false)
  }, [cancel])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort()
      }
    }
  }, [])

  // Execute immediately if requested
  useEffect(() => {
    if (options?.immediate) {
      execute()
    }
  }, [options?.immediate, execute])

  return { data, loading, error, execute, cancel, reset }
}

/**
 * useCancellableEffect - A simpler hook for one-off cancellable effects
 *
 * Usage:
 *   useCancellableEffect(
 *     async (signal) => {
 *       const result = await api.talents.list({}, { signal })
 *       setResults(result.data)
 *     },
 *     [dep1, dep2]
 *   )
 */
export function useCancellableEffect(
  effect: (signal: AbortSignal) => Promise<void>,
  deps: React.DependencyList
): void {
  useEffect(() => {
    const controller = new AbortController()

    effect(controller.signal).catch((err) => {
      if (!isCancellationError(err)) {
        console.error('Effect error:', err)
      }
    })

    return () => {
      controller.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

export default useCancellableRequest

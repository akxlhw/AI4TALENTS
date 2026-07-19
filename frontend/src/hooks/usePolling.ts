import { useEffect, useRef } from 'react'

interface UsePollingOptions {
  /** Called once immediately and then every `interval` ms while `enabled`. */
  callback: () => void | Promise<void>
  interval?: number
  enabled?: boolean
}

/**
 * Declarative polling: runs `callback` every `interval` while `enabled`,
 * always cleans up on unmount or when `enabled` flips to false.
 * No hard time cap — stop conditions belong in the `enabled` expression
 * (e.g. `enabled: status === 'running'`), so a task can never get stuck
 * on a dead "running" UI after a timeout.
 */
export function usePolling({ callback, interval = 2000, enabled = true }: UsePollingOptions) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  })

  useEffect(() => {
    if (!enabled) return
    let stopped = false
    const tick = async () => {
      if (!stopped) await savedCallback.current()
    }
    void tick()
    const id = setInterval(tick, interval)
    return () => {
      stopped = true
      clearInterval(id)
    }
  }, [enabled, interval])
}

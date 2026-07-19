import type { NavigateFunction } from 'react-router-dom'

/**
 * Navigate back when in-app history exists; otherwise go to a safe fallback.
 * Prevents "back" from leaving the site when a detail page is opened via a
 * shared link (no prior in-app history entry).
 */
export function navigateBack(navigate: NavigateFunction, fallback: string) {
  const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0
  if (idx > 0) {
    navigate(-1)
  } else {
    navigate(fallback)
  }
}

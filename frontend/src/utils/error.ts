/**
 * Error handling utilities.
 */

/**
 * Extract a human-readable error message from an unknown error.
 *
 * Handles Axios-style errors with `response.data.detail`,
 * falls back to `error.message`, then to `defaultMsg`.
 */
export const getErrorMessage = (error: unknown, defaultMsg: string): string => {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: { detail?: string } }; message?: string }
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail
      return typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    if (axiosError.message) {
      return axiosError.message
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return defaultMsg
}

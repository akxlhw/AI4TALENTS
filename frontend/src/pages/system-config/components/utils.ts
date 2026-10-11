/**
 * Shared utilities for system configuration tabs.
 */
import { i18n } from '../../../i18n'

/**
 * Extract a human-readable message from an unknown error.
 *
 * Backward compatible: existing callers may keep passing a hardcoded
 * `defaultMsg` (returned as-is). Prefer the i18n path instead — pass
 * `undefined` for `defaultMsg` and a `fallbackKey` resolved against the
 * `common` namespace (e.g. 'messages.operationFailed'); when neither is
 * given, the generic common:messages.operationFailed message is returned
 * in the active language.
 */
export const getErrorMessage = (
  error: unknown,
  defaultMsg?: string,
  fallbackKey?: string
): string => {
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
  if (fallbackKey) {
    return i18n.t(fallbackKey, { ns: 'common' })
  }
  return defaultMsg ?? i18n.t('messages.operationFailed', { ns: 'common' })
}

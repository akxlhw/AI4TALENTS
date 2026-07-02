/**
 * Unified API export
 * Aggregates domain-specific APIs into a single api object
 */
export { apiClient, createCancellableRequest, isCancellationError } from './api/client'
export type { CancellableRequestConfig } from './api/client'

import { sharedApi } from './api/shared'
import { academicApi } from './api/academic'
import { openSourceApi } from './api/openSource'
import { labApi } from './api/lab'

export const api = {
  ...sharedApi,
  ...academicApi,
  openSource: openSourceApi,
  lab: labApi,
}

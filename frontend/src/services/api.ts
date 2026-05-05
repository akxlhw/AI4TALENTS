/**
 * API client for backend communication
 *
 * @deprecated This monolithic API file has been refactored into domain-specific modules:
 *   - services/api/client.ts - Axios client and utilities
 *   - services/api/shared.ts - Shared APIs (auth, admin, system-config)
 *   - services/api/academic.ts - Academic talent APIs
 *   - services/api/openSource.ts - Open source talent APIs
 *
 * For new code, prefer importing from the domain-specific modules.
 */

export { apiClient, createCancellableRequest, isCancellationError } from './api/client'
export type { CancellableRequestConfig } from './api/client'

import { sharedApi } from './api/shared'
import { academicApi } from './api/academic'
import { openSourceApi } from './api/openSource'

export const api = {
  ...sharedApi,
  ...academicApi,
  openSource: openSourceApi,
}

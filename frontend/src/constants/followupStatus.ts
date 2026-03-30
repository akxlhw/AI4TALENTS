/**
 * Followup Status Constants
 *
 * Unified followup status definitions for talent pipeline management.
 * Used in favorites, talent pools, and talent detail views.
 */

export interface FollowupStatusConfig {
  color: string
  text: string
}

/**
 * Followup status display configuration map
 */
export const FOLLOWUP_STATUS_MAP: Record<string, FollowupStatusConfig> = {
  new_found: { color: 'blue', text: '新发现' },
  reviewed: { color: 'cyan', text: '已审阅' },
  followed: { color: 'green', text: '已跟进' },
  pending_evaluation: { color: 'orange', text: '待评估' },
  recommend_contact: { color: 'purple', text: '推荐联系' },
  no_followup: { color: 'default', text: '暂不跟进' },
}

/**
 * Get followup status config with fallback
 */
export function getFollowupStatusConfig(status: string): FollowupStatusConfig {
  return FOLLOWUP_STATUS_MAP[status] || { color: 'default', text: status }
}

/**
 * Get followup status display text
 */
export function getFollowupStatusText(status: string): string {
  return getFollowupStatusConfig(status).text
}

/**
 * Get followup status color
 */
export function getFollowupStatusColor(status: string): string {
  return getFollowupStatusConfig(status).color
}

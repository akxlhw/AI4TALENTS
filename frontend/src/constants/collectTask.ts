/**
 * Collect Task Constants
 *
 * Unified constants for collect task management.
 * Used in collect page and related components.
 */

import type { TaskStatusConfig, CollectModeConfig, VenueTypeConfig } from '../types'

/**
 * Task status display configuration map
 */
export const TASK_STATUS_MAP: Record<string, TaskStatusConfig> = {
  pending: { label: '待执行', color: 'default', status: 'default' },
  running: { label: '执行中', color: 'processing', status: 'processing' },
  completed: { label: '已完成', color: 'success', status: 'success' },
  failed: { label: '失败', color: 'error', status: 'error' },
  cancelled: { label: '已取消', color: 'warning', status: 'warning' },
}

/**
 * Collect mode display configuration map
 */
export const COLLECT_MODE_MAP: Record<string, CollectModeConfig> = {
  full: { label: '全量采集', color: 'blue' },
  incremental: { label: '增量采集', color: 'green' },
}

/**
 * Venue type display configuration map
 */
export const VENUE_TYPE_MAP: Record<string, VenueTypeConfig> = {
  conference: { label: '会议', color: 'blue' },
  journal: { label: '期刊', color: 'purple' },
  workshop: { label: '研讨会', color: 'cyan' },
}

/**
 * Get task status config with fallback
 */
export function getTaskStatusConfig(status: string): TaskStatusConfig {
  return TASK_STATUS_MAP[status] || {
    label: status,
    color: 'default',
    status: 'default',
  }
}

/**
 * Get collect mode config with fallback
 */
export function getCollectModeConfig(mode: string): CollectModeConfig {
  return COLLECT_MODE_MAP[mode] || { label: mode, color: 'default' }
}

/**
 * Get venue type config with fallback
 */
export function getVenueTypeConfig(type: string): VenueTypeConfig {
  return VENUE_TYPE_MAP[type] || { label: type, color: 'default' }
}

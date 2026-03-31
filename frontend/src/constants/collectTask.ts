/**
 * Collect Task Constants
 *
 * Unified constants for collect task management.
 * Used in collect page and related components.
 */

import type { TaskStatusConfig, VenueTypeConfig } from '../types'

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
 * Venue type display configuration map
 */
export const VENUE_TYPE_MAP: Record<string, VenueTypeConfig> = {
  conference: { label: '会议', color: 'blue' },
  journal: { label: '期刊', color: 'purple' },
  workshop: { label: '研讨会', color: 'cyan' },
}

/**
 * Time range configuration
 */
export const TIME_RANGE_CONFIG = {
  MIN_START_YEAR: 2015,
  DEFAULT_START_YEAR: 2020,
}

/**
 * Get current year
 */
export function getCurrentYear(): number {
  return new Date().getFullYear()
}

/**
 * Get start year options
 */
export function getStartYearOptions(): Array<{ value: number; label: string }> {
  const currentYear = getCurrentYear()
  const options = []
  for (let year = currentYear; year >= TIME_RANGE_CONFIG.MIN_START_YEAR; year--) {
    options.push({ value: year, label: `${year}年` })
  }
  return options
}

/**
 * Get end year options based on start year
 */
export function getEndYearOptions(startYear: number): Array<{ value: number | null; label: string }> {
  const currentYear = getCurrentYear()
  const options: Array<{ value: number | null; label: string }> = [
    { value: null, label: '至今' }
  ]
  for (let year = currentYear; year >= startYear; year--) {
    options.push({ value: year, label: `${year}年` })
  }
  return options
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
 * Get venue type config with fallback
 */
export function getVenueTypeConfig(type: string): VenueTypeConfig {
  return VENUE_TYPE_MAP[type] || { label: type, color: 'default' }
}

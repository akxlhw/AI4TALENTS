/**
 * Collect Task Constants
 *
 * Unified constants for collect task management.
 * Used in collect page and related components.
 *
 * i18n: map labels hold i18n KEYS (common namespace) — translate at render
 * time via useCollectTaskConfig() (components) or t(); the plain getters
 * translate through the i18n instance so legacy callers keep working.
 */

import { useTranslation } from 'react-i18next'
import { i18n } from '../i18n'

import type { TaskStatusConfig, VenueTypeConfig } from '../types'

/**
 * Task status display configuration map.
 * NOTE: `label` holds an i18n KEY — translate with t() or useCollectTaskConfig().
 */
export const TASK_STATUS_MAP: Record<string, TaskStatusConfig> = {
  pending: { label: 'common:taskStatus.pending', color: 'default', status: 'default' },
  running: { label: 'common:taskStatus.running', color: 'processing', status: 'processing' },
  completed: { label: 'common:taskStatus.completed', color: 'success', status: 'success' },
  failed: { label: 'common:taskStatus.failed', color: 'error', status: 'error' },
  cancelled: { label: 'common:taskStatus.cancelled', color: 'warning', status: 'warning' },
}

/**
 * Venue type display configuration map.
 * NOTE: `label` holds an i18n KEY — translate with t() or useCollectTaskConfig().
 */
export const VENUE_TYPE_MAP: Record<string, VenueTypeConfig> = {
  conference: { label: 'common:venueType.conference', color: 'blue' },
  journal: { label: 'common:venueType.journal', color: 'purple' },
  workshop: { label: 'common:venueType.workshop', color: 'cyan' },
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
    options.push({ value: year, label: getYearLabel(year) })
  }
  return options
}

/**
 * Get end year options based on start year
 */
export function getEndYearOptions(startYear: number): Array<{ value: number | null; label: string }> {
  const currentYear = getCurrentYear()
  const options: Array<{ value: number | null; label: string }> = [
    { value: null, label: i18n.t('yearOptions.endYear', { ns: 'common' }) },
  ]
  for (let year = currentYear; year >= startYear; year--) {
    options.push({ value: year, label: getYearLabel(year) })
  }
  return options
}

/** Translated "<year> 年" label (en: bare year). */
export const getYearLabel = (year: number): string =>
  i18n.t('yearOptions.year', { ns: 'common', year })

/**
 * Get task status config with fallback
 *
 * @param status - Task status string
 * @returns TaskStatusConfig with translated label
 */
export function getTaskStatusConfig(status: string): TaskStatusConfig {
  const base = TASK_STATUS_MAP[status] || {
    label: status,
    color: 'default',
    status: 'default',
  }
  return { ...base, label: i18n.t(`taskStatus.${status}`, { ns: 'common', defaultValue: status }) }
}

/**
 * Get venue type config with fallback
 *
 * @param type - Venue type string
 * @returns VenueTypeConfig with translated label
 */
export function getVenueTypeConfig(type: string): VenueTypeConfig {
  const base = VENUE_TYPE_MAP[type] || { label: type, color: 'default' }
  return { ...base, label: i18n.t(`venueType.${type}`, { ns: 'common', defaultValue: type }) }
}

/** Render-side translated collect-task labels (components only). */
export const useCollectTaskConfig = () => {
  const { t } = useTranslation('common')
  return {
    taskStatusLabel: (status: string) =>
      t(`taskStatus.${status}`, { defaultValue: status }),
    taskStatusConfig: (status: string): TaskStatusConfig => ({
      ...(TASK_STATUS_MAP[status] || { label: status, color: 'default', status: 'default' }),
      label: t(`taskStatus.${status}`, { defaultValue: status }),
    }),
    venueTypeLabel: (type: string) => t(`venueType.${type}`, { defaultValue: type }),
    venueTypeConfig: (type: string): VenueTypeConfig => ({
      ...(VENUE_TYPE_MAP[type] || { label: type, color: 'default' }),
      label: t(`venueType.${type}`, { defaultValue: type }),
    }),
    startYearOptions: (): Array<{ value: number; label: string }> =>
      getStartYearOptions(),
    endYearOptions: (startYear: number): Array<{ value: number | null; label: string }> =>
      getEndYearOptions(startYear),
  }
}

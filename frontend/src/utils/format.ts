/**
 * Format utilities for consistent data display
 */

/**
 * Format a number with locale-specific formatting
 *
 * @param value - Number to format
 * @param options - Intl.NumberFormat options
 * @returns Formatted number string, or '-' for null/undefined
 *
 * @example
 * formatNumber(1234567) // '1,234,567'
 * formatNumber(null) // '-'
 * formatNumber(0.1234, { style: 'percent', minimumFractionDigits: 1 }) // '12.3%'
 */
export function formatNumber(
  value: number | null | undefined,
  options?: Intl.NumberFormatOptions
): string {
  if (value == null) return '-'
  if (typeof value !== 'number' || isNaN(value)) return '-'
  return value.toLocaleString('zh-CN', options)
}

/**
 * Format a number as compact (e.g., 1.2K, 3.5M)
 *
 * @param value - Number to format
 * @returns Compact formatted string
 *
 * @example
 * formatCompactNumber(1234567) // '123万'
 * formatCompactNumber(1234) // '1,234'
 */
export function formatCompactNumber(value: number | null | undefined): string {
  if (value == null) return '-'
  if (typeof value !== 'number' || isNaN(value)) return '-'

  if (value >= 100000000) {
    return `${(value / 100000000).toFixed(1)}亿`
  }
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万`
  }
  return value.toLocaleString('zh-CN')
}

/**
 * Format a percentage value
 *
 * @param value - Number to format as percentage (0-1 range)
 * @param fractionDigits - Number of fraction digits (default: 1)
 * @returns Formatted percentage string
 *
 * @example
 * formatPercent(0.856) // '85.6%'
 * formatPercent(1) // '100.0%'
 */
export function formatPercent(
  value: number | null | undefined,
  fractionDigits: number = 1
): string {
  if (value == null) return '-'
  if (typeof value !== 'number' || isNaN(value)) return '-'
  return `${(value * 100).toFixed(fractionDigits)}%`
}

/**
 * Format a file size in bytes to human readable
 *
 * @param bytes - File size in bytes
 * @returns Human readable file size
 *
 * @example
 * formatFileSize(1024) // '1 KB'
 * formatFileSize(1536000) // '1.46 MB'
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes == null) return '-'
  if (bytes === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${units[i]}`
}

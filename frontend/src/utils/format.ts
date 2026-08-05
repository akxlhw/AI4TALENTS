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

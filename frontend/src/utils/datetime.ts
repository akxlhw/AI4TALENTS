/**
 * 时间格式化工具
 *
 * 后端存储的是 UTC 时间，前端显示时需要转换为本地时间
 */

/**
 * 将 UTC 时间字符串转换为本地时间字符串
 *
 * @param utcString - UTC 时间字符串（如 "2026-04-13T17:08:01" 或 "2026-04-13T17:08:01.442375"）
 * @param options - Intl.DateTimeFormatOptions 选项
 * @returns 本地时间字符串，如果输入为空则返回 '-'
 *
 * @example
 * formatUTCToLocal('2026-04-13T17:08:01') // 在东八区返回 "2026/4/14 01:08:01"
 */
export function formatUTCToLocal(
  utcString: string | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!utcString) return '-'

  try {
    // 后端返回的是 UTC 时间，需要添加 'Z' 后缀让 JavaScript 正确解析
    const utcTime = utcString.endsWith('Z') ? utcString : `${utcString}Z`
    const date = new Date(utcTime)

    // 默认格式化选项
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }

    return date.toLocaleString('zh-CN', options || defaultOptions)
  } catch {
    return utcString
  }
}

/**
 * 将 UTC 时间字符串转换为本地日期字符串（不含时间）
 *
 * @param utcString - UTC 时间字符串
 * @returns 本地日期字符串，如 "2026/4/14"
 */
export function formatUTCToLocalDate(utcString: string | null | undefined): string {
  return formatUTCToLocal(utcString, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/**
 * 将 UTC 时间字符串转换为相对时间描述
 *
 * @param utcString - UTC 时间字符串
 * @returns 相对时间描述，如 "3分钟前"、"2小时前"
 */
export function formatUTCToRelative(utcString: string | null | undefined): string {
  if (!utcString) return '-'

  try {
    const utcTime = utcString.endsWith('Z') ? utcString : `${utcString}Z`
    const date = new Date(utcTime)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSeconds < 60) return '刚刚'
    if (diffMinutes < 60) return `${diffMinutes}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return formatUTCToLocal(utcString)
  } catch {
    return utcString
  }
}

/**
 * 获取当前本地时间的 ISO 字符串（用于提交到后端）
 *
 * @returns ISO 格式的本地时间字符串
 */
export function getLocalISOTime(): string {
  const now = new Date()
  // 转换为本地时间的 ISO 字符串
  const offset = now.getTimezoneOffset()
  const localTime = new Date(now.getTime() - offset * 60 * 1000)
  return localTime.toISOString().slice(0, -1) // 移除 'Z'
}

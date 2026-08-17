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
 * 将后端「本地墙钟」时间字符串按原样格式化展示。
 *
 * 项目中 TimestampMixin 的 created_at/updated_at 由数据库 func.now() 默认值
 * 写入，DB 会话时区为 Asia/Shanghai，因此这些列存储的已是北京墙钟时间，
 * 前端不得再做时区换算（否则会 +8h）。仅用于确认存储为 DB 本地时间的列；
 * 代码里以 naive UTC 写入的字段（如 started_at/completed_at）仍用
 * formatUTCToLocal。
 */
export function formatDBLocal(
  localString: string | null | undefined
): string {
  if (!localString) return '-'
  // Naive "2026-08-16T16:19:51.911" — normalize to "YYYY-MM-DD HH:mm:ss"
  const m = localString.replace('T', ' ').match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/)
  return m ? m[1] : localString
}

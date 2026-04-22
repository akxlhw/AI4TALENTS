/**
 * Tests for format utilities
 */
import { describe, it, expect } from 'vitest'
import { formatNumber, formatCompactNumber, formatPercent, formatFileSize } from './format'

describe('formatNumber', () => {
  it('should format positive numbers with locale', () => {
    expect(formatNumber(1234567)).toBe('1,234,567')
    expect(formatNumber(100)).toBe('100')
    expect(formatNumber(0)).toBe('0')
  })

  it('should return "-" for null/undefined', () => {
    expect(formatNumber(null)).toBe('-')
    expect(formatNumber(undefined)).toBe('-')
  })

  it('should return "-" for NaN', () => {
    expect(formatNumber(NaN)).toBe('-')
  })

  it('should support Intl.NumberFormat options', () => {
    expect(formatNumber(0.1234, { style: 'percent', minimumFractionDigits: 1 })).toBe('12.3%')
    expect(formatNumber(1234.56, { minimumFractionDigits: 2 })).toBe('1,234.56')
  })

  it('should handle negative numbers', () => {
    expect(formatNumber(-1234)).toBe('-1,234')
  })
})

describe('formatCompactNumber', () => {
  it('should format numbers >= 10000 with 万 unit', () => {
    expect(formatCompactNumber(1234567)).toBe('123.5万')
    expect(formatCompactNumber(10000)).toBe('1.0万')
    expect(formatCompactNumber(50000)).toBe('5.0万')
  })

  it('should format numbers >= 100000000 with 亿 unit', () => {
    expect(formatCompactNumber(123456789)).toBe('1.2亿')
    expect(formatCompactNumber(100000000)).toBe('1.0亿')
  })

  it('should return "-" for null/undefined', () => {
    expect(formatCompactNumber(null)).toBe('-')
    expect(formatCompactNumber(undefined)).toBe('-')
  })

  it('should return "-" for NaN', () => {
    expect(formatCompactNumber(NaN)).toBe('-')
  })

  it('should format small numbers normally', () => {
    expect(formatCompactNumber(1234)).toBe('1,234')
    expect(formatCompactNumber(999)).toBe('999')
  })
})

describe('formatPercent', () => {
  it('should format decimal as percentage', () => {
    expect(formatPercent(0.856)).toBe('85.6%')
    expect(formatPercent(1)).toBe('100.0%')
    expect(formatPercent(0)).toBe('0.0%')
    expect(formatPercent(0.5)).toBe('50.0%')
  })

  it('should return "-" for null/undefined', () => {
    expect(formatPercent(null)).toBe('-')
    expect(formatPercent(undefined)).toBe('-')
  })

  it('should return "-" for NaN', () => {
    expect(formatPercent(NaN)).toBe('-')
  })

  it('should support custom fraction digits', () => {
    expect(formatPercent(0.856, 2)).toBe('85.60%')
    expect(formatPercent(0.5, 0)).toBe('50%')
  })
})

describe('formatFileSize', () => {
  it('should format bytes', () => {
    expect(formatFileSize(500)).toBe('500 B')
    expect(formatFileSize(0)).toBe('0 B')
  })

  it('should format kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
    expect(formatFileSize(1536)).toBe('1.5 KB')
  })

  it('should format megabytes', () => {
    expect(formatFileSize(1536000)).toBe('1.46 MB')
    expect(formatFileSize(1048576)).toBe('1 MB')
  })

  it('should format gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB')
    expect(formatFileSize(2147483648)).toBe('2 GB')
  })

  it('should return "-" for null/undefined', () => {
    expect(formatFileSize(null)).toBe('-')
    expect(formatFileSize(undefined)).toBe('-')
  })
})

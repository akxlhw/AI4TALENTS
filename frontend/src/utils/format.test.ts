/**
 * Tests for format utilities
 */
import { describe, it, expect } from 'vitest'
import { formatNumber } from './format'

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

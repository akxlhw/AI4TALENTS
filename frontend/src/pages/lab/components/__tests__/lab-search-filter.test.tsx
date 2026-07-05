import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LabSearchFilter from '../lab-search-filter'

describe('LabSearchFilter', () => {
  const mockState = {
    keyword: '',
    parentLab: '',
    labName: '',
    roleType: '',
    academicLevel: '',
    researchArea: '',
    sortBy: 'default' as const,
    page: 1,
    pageSize: 20,
    advancedOpen: false,
    setFilter: vi.fn(),
    resetFilters: vi.fn(),
    toggleAdvanced: vi.fn(),
    syncFromUrl: vi.fn(),
    toQuery: vi.fn(() => ({})),
  }

  it('renders core filters', () => {
    render(<LabSearchFilter state={mockState} />)
    expect(screen.getByPlaceholderText('输入姓名关键词...')).toBeInTheDocument()
    expect(screen.getByText('高级筛选')).toBeInTheDocument()
    expect(screen.getByText('重置')).toBeInTheDocument()
  })

  it('calls resetFilters when reset clicked', () => {
    render(<LabSearchFilter state={mockState} />)
    fireEvent.click(screen.getByText('重置'))
    expect(mockState.resetFilters).toHaveBeenCalled()
  })

  it('toggles advanced filters', () => {
    render(<LabSearchFilter state={mockState} />)
    fireEvent.click(screen.getByText('高级筛选'))
    expect(mockState.toggleAdvanced).toHaveBeenCalled()
  })
})

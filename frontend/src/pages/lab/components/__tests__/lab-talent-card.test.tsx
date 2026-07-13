import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LabTalentCard from '../lab-talent-card'
import type { LabTalent } from '../../../../types'

const mockTalent: LabTalent = {
  talent_id: 1,
  name: '周志华',
  role_section: 'faculty',
  role_type: 'professor',
  academic_level: 'phd',
  current_title: '南京大学特聘教授',
  homepage: null,
  email: null,
  photo_url: null,
  department: null,
  research_areas: ['machine learning', 'data mining'],
  cohort_year: null,
  lab_name: 'LAMDA',
  parent_lab: '南京大学LAMDA实验室',
  lab_logo_url: null,
}

describe('LabTalentCard', () => {
  it('renders name, role and research areas', () => {
    render(
      <MemoryRouter>
        <LabTalentCard talent={mockTalent} />
      </MemoryRouter>
    )
    expect(screen.getByText('周志华')).toBeInTheDocument()
    expect(screen.getByText('教授')).toBeInTheDocument()
    expect(screen.getByText('博士')).toBeInTheDocument()
    expect(screen.getByText('machine learning')).toBeInTheDocument()
  })

  it('truncates research areas with +N', () => {
    const manyAreas = { ...mockTalent, research_areas: ['a', 'b', 'c', 'd', 'e'] }
    render(
      <MemoryRouter>
        <LabTalentCard talent={manyAreas} />
      </MemoryRouter>
    )
    expect(screen.getByText('+2')).toBeInTheDocument()
  })
})

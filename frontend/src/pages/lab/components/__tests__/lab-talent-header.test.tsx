import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LabTalentHeader from '../lab-talent-header'
import type { LabTalentDetail } from '../../../../types'

const mockTalent: LabTalentDetail = {
  talent_id: 1,
  name: '周志华',
  role_section: 'faculty',
  role_type: 'professor',
  academic_level: 'phd',
  current_title: '南京大学特聘教授',
  homepage: 'http://cs.nju.edu.cn/zhouzh',
  email: 'zhouzh@nju.edu.cn',
  photo_url: null,
  department: '计算机系',
  research_areas: ['machine learning'],
  cohort_year: null,
  lab_name: 'LAMDA',
  parent_lab: '南京大学LAMDA实验室',
  lab_logo_url: null,
  cohort_source: null,
  source_url: null,
  source_detail_url: null,
  collected_at: null,
}

describe('LabTalentHeader', () => {
  it('renders name, role and contact buttons', () => {
    render(<LabTalentHeader talent={mockTalent} />)
    expect(screen.getByText('周志华')).toBeInTheDocument()
    expect(screen.getByText('教授')).toBeInTheDocument()
    expect(screen.getByText('zhouzh@nju.edu.cn')).toBeInTheDocument()
    expect(screen.getByText('个人主页')).toBeInTheDocument()
  })
})

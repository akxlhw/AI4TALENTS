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
  social_links: {},
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

  it('renders no social anchors when social_links is empty', () => {
    const { container } = render(<LabTalentHeader talent={mockTalent} />)
    // only email (mailto:) + homepage anchors
    expect(container.querySelectorAll('a')).toHaveLength(2)
  })

  it('renders social link anchors opening in new tab', () => {
    const talent: LabTalentDetail = {
      ...mockTalent,
      social_links: {
        linkedin: 'https://www.linkedin.com/in/zhouzh',
        github: 'https://github.com/zhouzh',
        homepage_blog: 'https://blog.example.com', // unknown platform → fallback icon
      },
    }
    const { container } = render(<LabTalentHeader talent={talent} />)
    const linkedin = container.querySelector('a[href="https://www.linkedin.com/in/zhouzh"]')
    expect(linkedin).not.toBeNull()
    expect(linkedin).toHaveAttribute('target', '_blank')
    expect(container.querySelector('a[href="https://github.com/zhouzh"]')).not.toBeNull()
    expect(container.querySelector('a[href="https://blog.example.com"]')).not.toBeNull()
  })
})

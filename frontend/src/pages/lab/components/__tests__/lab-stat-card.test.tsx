import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UserOutlined } from '@ant-design/icons'
import LabStatCard from '../lab-stat-card'

describe('LabStatCard', () => {
  it('renders title and value', () => {
    render(<LabStatCard title="人才总数" value={108} icon={<UserOutlined data-testid="user-icon" />} />)
    expect(screen.getByText('人才总数')).toBeInTheDocument()
    expect(screen.getByText('108')).toBeInTheDocument()
    expect(screen.getByTestId('user-icon')).toBeInTheDocument()
  })
})

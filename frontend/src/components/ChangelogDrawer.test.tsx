import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import ChangelogDrawer from './ChangelogDrawer'

describe('ChangelogDrawer', () => {
  it('renders the latest version badge and group tags when open', () => {
    render(<ChangelogDrawer open onClose={vi.fn()} />)
    expect(screen.getAllByText('最新').length).toBeGreaterThan(0)
    expect(screen.getByText('Added')).toBeTruthy()
    expect(screen.getByText('Changed')).toBeTruthy()
    expect(screen.getByText('Fixed')).toBeTruthy()
  })

  it('shows an empty state when nothing parsed', () => {
    render(<ChangelogDrawer open onClose={vi.fn()} forceEmpty />)
    expect(screen.getByText('暂无更新记录')).toBeTruthy()
  })

  it('calls onClose when the drawer close button is clicked', () => {
    const onClose = vi.fn()
    render(<ChangelogDrawer open onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

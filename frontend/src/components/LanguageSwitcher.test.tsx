import { describe, expect, it, beforeEach, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import '../i18n'
import LanguageSwitcher from './LanguageSwitcher'

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders with zh selected by default and switches to en on click', async () => {
    render(<LanguageSwitcher />)

    // default zh: nav.favorites renders in Chinese somewhere via i18n state
    const { i18n } = await import('../i18n')
    await i18n.changeLanguage('zh')
    expect(i18n.language).toBe('zh')

    // click the EN option (segmented radio labeled EN)
    const enOption = screen.getByText('EN', { selector: '.ant-segmented-item-label' })
    fireEvent.click(enOption)

    await waitFor(() => expect(i18n.language).toBe('en'))
    expect(localStorage.getItem('i18n_lang')).toBe('en')

    // switch back to zh persists
    const zhOption = screen.getByText('中', { selector: '.ant-segmented-item-label' })
    fireEvent.click(zhOption)
    await waitFor(() => expect(i18n.language).toBe('zh'))
    expect(localStorage.getItem('i18n_lang')).toBe('zh')
  })
})

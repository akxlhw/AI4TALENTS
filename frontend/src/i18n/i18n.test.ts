import { describe, expect, it, beforeEach } from 'vitest'

describe('i18n init', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to zh when nothing persisted', async () => {
    const { i18n } = await import('./index')
    expect(i18n.language).not.toBe('en')
    expect(i18n.t('nav:favorites')).toBe('我的收藏')
  })

  it('switching language persists and translates both ways', async () => {
    const { i18n } = await import('./index')
    await i18n.changeLanguage('en')
    expect(localStorage.getItem('i18n_lang')).toBe('en')
    expect(i18n.t('nav:favorites')).toBe('Favorites')
    expect(i18n.t('common:pagination.total', { n: 42 })).toBe('42 items')

    await i18n.changeLanguage('zh')
    expect(localStorage.getItem('i18n_lang')).toBe('zh')
    expect(i18n.t('common:pagination.total', { n: 42 })).toBe('共 42 条')
  })
})

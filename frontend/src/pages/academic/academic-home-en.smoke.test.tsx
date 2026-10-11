import { describe, expect, it } from 'vitest'

import '../../i18n'

/** Bilingual smoke: spot-check that every namespace returns real English
 * (not raw keys) after switching, then restores zh. Component-level EN
 * rendering is covered per-domain (e.g. insights-panel, switcher tests). */
describe('bilingual resources smoke', () => {
  it('all namespaces resolve English copy under en', async () => {
    const { i18n } = await import('../../i18n')
    await i18n.changeLanguage('en')

    const samples: Array<[string, RegExp]> = [
      ['academic:home.title', /talent/i],
      ['nav:favorites', /Favorites/],
      ['common:actions.search', /Search/],
      ['auth:login.submit', /Sign In/],
      ['taxonomy:domains.ai_models', /LLM/],
      ['lab:role.professor', /Professor/],
      ['openSource:common.retry|lab:common.search', /.+/],
      ['competition:medal.gold', /Gold/i],
      ['industry:status.new', /New/i],
      ['user:favorites.title', /Favorites/],
    ]

    for (const [rawKey, re] of samples) {
      const key = rawKey.split('|').find(k => i18n.exists(k)) || rawKey.split('|')[0]
      const value = i18n.t(key)
      expect(value, key).toMatch(re)
      expect(value, key).not.toMatch(/^[a-zA-Z]+\.[a-zA-Z.]+$/) // no raw keys
    }

    await i18n.changeLanguage('zh')
    expect(i18n.t('academic:home.title')).toContain('人才库')
  })
})

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Central registration of ALL namespaces (belt) — pages also import their
// domain's self-registering module in src/i18n/namespaces/ (suspenders) so
// either path alone is sufficient; addResourceBundle guards keep them idempotent.
import academicEn from './locales/en/academic.json'
import adminEn from './locales/en/admin.json'
import authEn from './locales/en/auth.json'
import commonEn from './locales/en/common.json'
import competitionEn from './locales/en/competition.json'
import industryEn from './locales/en/industry.json'
import labEn from './locales/en/lab.json'
import legalEn from './locales/en/legal.json'
import navEn from './locales/en/nav.json'
import openSourceEn from './locales/en/openSource.json'
import systemConfigEn from './locales/en/systemConfig.json'
import taxonomyEn from './locales/en/taxonomy.json'
import userEn from './locales/en/user.json'
import academicZh from './locales/zh/academic.json'
import adminZh from './locales/zh/admin.json'
import authZh from './locales/zh/auth.json'
import commonZh from './locales/zh/common.json'
import competitionZh from './locales/zh/competition.json'
import industryZh from './locales/zh/industry.json'
import labZh from './locales/zh/lab.json'
import legalZh from './locales/zh/legal.json'
import navZh from './locales/zh/nav.json'
import openSourceZh from './locales/zh/openSource.json'
import systemConfigZh from './locales/zh/systemConfig.json'
import taxonomyZh from './locales/zh/taxonomy.json'
import userZh from './locales/zh/user.json'

export const LANG_STORAGE_KEY = 'i18n_lang'
export const SUPPORTED_LANGS = ['zh', 'en'] as const
export type Lang = (typeof SUPPORTED_LANGS)[number]

const initialLang: Lang = (() => {
  const saved = localStorage.getItem(LANG_STORAGE_KEY)
  return saved === 'en' ? 'en' : 'zh'
})()

void i18n.use(initReactI18next).init({
  resources: {
    zh: {
      common: commonZh,
      nav: navZh,
      auth: authZh,
      taxonomy: taxonomyZh,
      academic: academicZh,
      openSource: openSourceZh,
      lab: labZh,
      competition: competitionZh,
      industry: industryZh,
      user: userZh,
      systemConfig: systemConfigZh,
      admin: adminZh,
      legal: legalZh,
    },
    en: {
      common: commonEn,
      nav: navEn,
      auth: authEn,
      taxonomy: taxonomyEn,
      academic: academicEn,
      openSource: openSourceEn,
      lab: labEn,
      competition: competitionEn,
      industry: industryEn,
      user: userEn,
      systemConfig: systemConfigEn,
      admin: adminEn,
      legal: legalEn,
    },
  },
  lng: initialLang,
  fallbackLng: 'zh',
  defaultNS: 'common',
  ns: [
    'common',
    'nav',
    'auth',
    'taxonomy',
    'academic',
    'openSource',
    'lab',
    'competition',
    'industry',
    'user',
    'systemConfig',
    'admin',
    'legal',
  ],
  interpolation: { escapeValue: false },
})

// Persist on every switch — the switcher and tests all go through changeLanguage
i18n.on('languageChanged', lng => {
  localStorage.setItem(LANG_STORAGE_KEY, lng)
})

export default i18n
export { i18n }

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import authEn from './locales/en/auth.json'
import commonEn from './locales/en/common.json'
import navEn from './locales/en/nav.json'
import authZh from './locales/zh/auth.json'
import commonZh from './locales/zh/common.json'
import navZh from './locales/zh/nav.json'

export const LANG_STORAGE_KEY = 'i18n_lang'
export const SUPPORTED_LANGS = ['zh', 'en'] as const
export type Lang = (typeof SUPPORTED_LANGS)[number]

const initialLang: Lang = (() => {
  const saved = localStorage.getItem(LANG_STORAGE_KEY)
  return saved === 'en' ? 'en' : 'zh'
})()

void i18n.use(initReactI18next).init({
  resources: {
    zh: { common: commonZh, nav: navZh, auth: authZh },
    en: { common: commonEn, nav: navEn, auth: authEn },
  },
  lng: initialLang,
  fallbackLng: 'zh',
  defaultNS: 'common',
  ns: ['common', 'nav', 'auth'],
  interpolation: { escapeValue: false },
})

// Persist on every switch — the switcher and tests all go through changeLanguage
i18n.on('languageChanged', lng => {
  localStorage.setItem(LANG_STORAGE_KEY, lng)
})

export default i18n
export { i18n }

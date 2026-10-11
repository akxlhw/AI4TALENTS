/**
 * Self-registering `industry` namespace.
 *
 * src/i18n/index.ts only registers common/nav/auth/taxonomy; per the project
 * convention, later domains register themselves here. Import this module from
 * any file that uses useTranslation('industry') or the label helpers in
 * pages/industry/constants/industry-config.ts — registration runs on import.
 */
import i18n from '../index'
import industryEn from '../locales/en/industry.json'
import industryZh from '../locales/zh/industry.json'

export function ensureIndustryNamespace(): void {
  if (!i18n.hasResourceBundle('zh', 'industry')) {
    i18n.addResourceBundle('zh', 'industry', industryZh, true, true)
  }
  if (!i18n.hasResourceBundle('en', 'industry')) {
    i18n.addResourceBundle('en', 'industry', industryEn, true, true)
  }
}

ensureIndustryNamespace()

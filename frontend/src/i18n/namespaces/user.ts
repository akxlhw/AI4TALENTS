/**
 * Self-registering `user` namespace (user area: favorites / talent pools /
 * feedback).
 *
 * src/i18n/index.ts only registers common/nav/auth/taxonomy; per the project
 * convention, later domains register themselves here. Import this module from
 * any file that uses useTranslation('user') — registration runs on import.
 */
import i18n from '../index'
import userEn from '../locales/en/user.json'
import userZh from '../locales/zh/user.json'

export function ensureUserNamespace(): void {
  if (!i18n.hasResourceBundle('zh', 'user')) {
    i18n.addResourceBundle('zh', 'user', userZh, true, true)
  }
  if (!i18n.hasResourceBundle('en', 'user')) {
    i18n.addResourceBundle('en', 'user', userEn, true, true)
  }
}

ensureUserNamespace()

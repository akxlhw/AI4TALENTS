/**
 * Admin i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `admin` namespace immediately available at runtime and
 * in tests regardless of that registration. Migrated components import this
 * module for its side effect.
 */
import { i18n } from '../index'
import adminZh from '../locales/zh/admin.json'
import adminEn from '../locales/en/admin.json'

const NS = 'admin'

export function ensureAdminNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? adminZh : adminEn)
    }
  }
}

ensureAdminNamespace()

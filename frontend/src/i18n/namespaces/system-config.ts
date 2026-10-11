/**
 * System config i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `systemConfig` namespace immediately available at runtime
 * and in tests regardless of that registration. Migrated components import
 * this module for its side effect.
 */
import { i18n } from '../index'
import systemConfigZh from '../locales/zh/systemConfig.json'
import systemConfigEn from '../locales/en/systemConfig.json'

const NS = 'systemConfig'

export function ensureSystemConfigNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? systemConfigZh : systemConfigEn)
    }
  }
}

ensureSystemConfigNamespace()

/**
 * Lab (AI Native) domain i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `lab` namespace immediately available at runtime and
 * in tests regardless of that registration. Migrated components import this
 * module for its side effect.
 */
import { i18n } from '../index'
import labZh from '../locales/zh/lab.json'
import labEn from '../locales/en/lab.json'

const NS = 'lab'

export function ensureLabNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? labZh : labEn)
    }
  }
}

ensureLabNamespace()

/**
 * Legal i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `legal` namespace immediately available at runtime and
 * in tests regardless of that registration. Migrated components import this
 * module for its side effect.
 */
import { i18n } from '../index'
import legalZh from '../locales/zh/legal.json'
import legalEn from '../locales/en/legal.json'

const NS = 'legal'

export function ensureLegalNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? legalZh : legalEn)
    }
  }
}

ensureLegalNamespace()

/**
 * Academic domain i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `academic` namespace immediately available at runtime and
 * in tests regardless of that registration. Migrated components import this
 * module for its side effect.
 */
import { i18n } from '../index'
import academicZh from '../locales/zh/academic.json'
import academicEn from '../locales/en/academic.json'

const NS = 'academic'

export function ensureAcademicNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? academicZh : academicEn)
    }
  }
}

ensureAcademicNamespace()

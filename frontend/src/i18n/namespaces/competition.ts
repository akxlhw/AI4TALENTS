/**
 * Competition domain i18n namespace — self-registration module.
 *
 * The mainline registers namespaces centrally in `src/i18n/index.ts`; this
 * module makes the `competition` namespace immediately available at runtime and
 * in tests regardless of that registration. Migrated components import this
 * module for its side effect.
 */
import { i18n } from '../index'
import competitionZh from '../locales/zh/competition.json'
import competitionEn from '../locales/en/competition.json'

const NS = 'competition'

export function ensureCompetitionNamespace(): void {
  for (const lng of ['zh', 'en'] as const) {
    if (!i18n.hasResourceBundle(lng, NS)) {
      i18n.addResourceBundle(lng, NS, lng === 'zh' ? competitionZh : competitionEn)
    }
  }
}

ensureCompetitionNamespace()

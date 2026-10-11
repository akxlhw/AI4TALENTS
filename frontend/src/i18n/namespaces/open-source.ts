/**
 * Self-registration for the `openSource` i18n namespace.
 *
 * `src/i18n/index.ts` stays domain-agnostic (it is off-limits during per-domain
 * i18n migrations), so each domain registers its own resource bundle here via a
 * side-effect import. Idempotent: registration is skipped once the bundle is
 * present — including if index.ts later bundles this namespace centrally.
 */
import i18n from '../index'
import en from '../locales/en/openSource.json'
import zh from '../locales/zh/openSource.json'

export function ensureOpenSourceNamespace(): void {
  if (!i18n.hasResourceBundle('zh', 'openSource')) {
    i18n.addResourceBundle('zh', 'openSource', zh)
  }
  if (!i18n.hasResourceBundle('en', 'openSource')) {
    i18n.addResourceBundle('en', 'openSource', en)
  }
}

ensureOpenSourceNamespace()

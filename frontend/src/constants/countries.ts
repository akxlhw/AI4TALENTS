import { useTranslation } from 'react-i18next'

/** Render-side country name translation, keyed by ISO-2 code (lowercase).
 * Unknown codes fall back to the API-provided name (zh) or the raw code. */
export const useCountryName = () => {
  const { t } = useTranslation('taxonomy')
  return (code: string | null | undefined, fallbackName?: string | null): string => {
    if (!code) return fallbackName || ''
    return t(`countries.${code.toLowerCase()}`, {
      defaultValue: fallbackName || code.toUpperCase(),
    })
  }
}

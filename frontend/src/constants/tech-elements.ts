/**
 * Tech element taxonomy (v2) — frontend mirror of
 * backend/app/domains/shared/constants/tech_taxonomy.py.
 * 10 domains → 34 elements (tech_element valid values) → 75 directions.
 * Update both files together.
 * Shared module — import from '@/constants/tech-elements'.
 */

export interface TechElementOption {
  value: string
  label: string
  color: string
  domain: string
}

// Domain display colors (one per domain, elements inherit)
const DOMAIN_COLORS: Record<string, string> = {
  basic_software: '#1A365D',
  ai_models: '#722ed1',
  ai_apps: '#9254de',
  communications: '#1677ff',
  computing: '#08979c',
  modeling_simulation: '#d4660a',
  trusted_security: '#cf1322',
  multimedia: '#eb2f96',
  robotics: '#389e0d',
  autonomous_driving: '#237804',
}

export const DOMAIN_LABEL_KEYS: Record<string, string> = {
  basic_software: 'taxonomy:domains.basic_software',
  ai_models: 'taxonomy:domains.ai_models',
  ai_apps: 'taxonomy:domains.ai_apps',
  communications: 'taxonomy:domains.communications',
  computing: 'taxonomy:domains.computing',
  modeling_simulation: 'taxonomy:domains.modeling_simulation',
  trusted_security: 'taxonomy:domains.trusted_security',
  multimedia: 'taxonomy:domains.multimedia',
  robotics: 'taxonomy:domains.robotics',
  autonomous_driving: 'taxonomy:domains.autonomous_driving',
}

// Flat list of 34 element codes with domain grouping + colors.
// NOTE: `label` holds an i18n KEY (taxonomy namespace) — translate at render
// time via useTechElements(); outside components use the key with t().
export const TECH_ELEMENTS: TechElementOption[] = [
  { value: 'os', label: 'taxonomy:elements.os', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'db_storage', label: 'taxonomy:elements.db_storage', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'languages', label: 'taxonomy:elements.languages', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'toolchain', label: 'taxonomy:elements.toolchain', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'middleware', label: 'taxonomy:elements.middleware', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'browser', label: 'taxonomy:elements.browser', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'models', label: 'taxonomy:elements.models', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  { value: 'training', label: 'taxonomy:elements.training', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  { value: 'inference', label: 'taxonomy:elements.inference', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  { value: 'agents', label: 'taxonomy:elements.agents', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  { value: 'ai_engineering', label: 'taxonomy:elements.ai_engineering', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  { value: 'apps', label: 'taxonomy:elements.apps', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  { value: 'protocols', label: 'taxonomy:elements.protocols', color: DOMAIN_COLORS.communications, domain: 'communications' },
  { value: 'wireless', label: 'taxonomy:elements.wireless', color: DOMAIN_COLORS.communications, domain: 'communications' },
  { value: 'network_simulation', label: 'taxonomy:elements.network_simulation', color: DOMAIN_COLORS.communications, domain: 'communications' },
  { value: 'hpc', label: 'taxonomy:elements.hpc', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'cloud_native', label: 'taxonomy:elements.cloud_native', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'virtualization', label: 'taxonomy:elements.virtualization', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'silicon', label: 'taxonomy:elements.silicon', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'sci_compute', label: 'taxonomy:elements.sci_compute', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  { value: 'simulation', label: 'taxonomy:elements.simulation', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  { value: 'math_libs', label: 'taxonomy:elements.math_libs', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  { value: 'sys_sec', label: 'taxonomy:elements.sys_sec', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  { value: 'sec_ops', label: 'taxonomy:elements.sec_ops', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  { value: 'crypto_trust', label: 'taxonomy:elements.crypto_trust', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  { value: 'av', label: 'taxonomy:elements.av', color: DOMAIN_COLORS.multimedia, domain: 'multimedia' },
  { value: 'graphics', label: 'taxonomy:elements.graphics', color: DOMAIN_COLORS.multimedia, domain: 'multimedia' },
  { value: 'robot_control', label: 'taxonomy:elements.robot_control', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  { value: 'robot_perception', label: 'taxonomy:elements.robot_perception', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  { value: 'embodied', label: 'taxonomy:elements.embodied', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  { value: 'ad_platforms', label: 'taxonomy:elements.ad_platforms', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_perception', label: 'taxonomy:elements.ad_perception', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_planning', label: 'taxonomy:elements.ad_planning', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_simulation', label: 'taxonomy:elements.ad_simulation', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
]

/** Options grouped by domain for OptGroup-style selects */
export const TECH_ELEMENT_GROUPS = Object.entries(
  TECH_ELEMENTS.reduce<Record<string, TechElementOption[]>>((acc, el) => {
    ;(acc[el.domain] = acc[el.domain] || []).push(el)
    return acc
  }, {})
).map(([domain, elements]) => ({
  label: DOMAIN_LABEL_KEYS[domain] || domain,
  options: elements.map(e => ({ value: e.value, label: e.label })),
}))

export const getTechElementLabel = (code: string): string =>
  TECH_ELEMENTS.find(t => t.value === code)?.label || `taxonomy:elements.${code}`

export const getTechElementColor = (code: string): string =>
  TECH_ELEMENTS.find(t => t.value === code)?.color || '#999'

/** "领域 · 要素" full label, e.g. "AI大模型 · 训练" — for surfaces where the
 * parent domain should be visible alongside the element. */
/** Full label composed of i18n KEYS — translate with useTechElements().fullLabel. */
export const getTechElementFullLabelKeys = (code: string): string => {
  const el = TECH_ELEMENTS.find(t => t.value === code)
  if (!el) return code
  return `${DOMAIN_LABEL_KEYS[el.domain] || el.domain}|${el.label}`
}

export const getTechElementDomain = (code: string): string | undefined =>
  TECH_ELEMENTS.find(t => t.value === code)?.domain

import { useTranslation } from 'react-i18next'

/** Render-side translated taxonomy labels (components only). */
export const useTechElements = () => {
  const { t } = useTranslation('taxonomy')
  return {
    domainLabel: (domain: string) => t(DOMAIN_LABEL_KEYS[domain] || '', { defaultValue: domain }),
    elementLabel: (code: string) => t(`elements.${code}`, { defaultValue: code }),
    fullLabel: (code: string) => {
      const domain = getTechElementDomain(code)
      if (!domain) return code
      return `${t(DOMAIN_LABEL_KEYS[domain] || '', { defaultValue: domain })} · ${t(`elements.${code}`, { defaultValue: code })}`
    },
  }
}

/**
 * Design System for AI4TALENTS — Multi-Domain Talent Platform
 *
 * Architecture: Neutral platform base + domain-aware tokens.
 * Current active domain: academic (学术人才).
 * Future domains: opensource, competition, industry — slots reserved.
 */

import type { ThemeConfig } from 'antd'

export type Domain = 'academic' | 'opensource' | 'lab' | 'competition' | 'industry'

export interface DomainTheme {
  key: Domain
  label: string
  shortLabel: string
  primary: string
  secondary: string
  gradient: string
  lightBg: string
  hoverBg: string
  badgeBg: string
  iconColor: string
}

export const domainThemes: Record<Domain, DomainTheme> = {
  academic: {
    key: 'academic',
    label: '学术人才',
    shortLabel: '学术',
    primary: '#1E3A5F',
    secondary: '#4A90A4',
    gradient: 'linear-gradient(135deg, #1E3A5F 0%, #2D5A87 50%, #4A90A4 100%)',
    lightBg: '#EEF4FA',
    hoverBg: '#DBEAFA',
    badgeBg: '#1E3A5F',
    iconColor: '#4A90A4',
  },
  opensource: {
    key: 'opensource',
    label: '开源生态',
    shortLabel: '开源',
    primary: '#2D3748',
    secondary: '#48BB78',
    gradient: 'linear-gradient(135deg, #2D3748 0%, #38A169 100%)',
    lightBg: '#F0FFF4',
    hoverBg: '#E6FFED',
    badgeBg: '#38A169',
    iconColor: '#48BB78',
  },
  competition: {
    key: 'competition',
    label: '竞赛人才',
    shortLabel: '竞赛',
    primary: '#1A202C',
    secondary: '#F6AD55',
    gradient: 'linear-gradient(135deg, #1A202C 0%, #DD6B20 100%)',
    lightBg: '#FFFAF0',
    hoverBg: '#FEEBCB',
    badgeBg: '#DD6B20',
    iconColor: '#F6AD55',
  },
  industry: {
    key: 'industry',
    label: '行业专家',
    shortLabel: '行业',
    primary: '#1A365D',
    secondary: '#805AD5',
    gradient: 'linear-gradient(135deg, #1A365D 0%, #6B46C1 100%)',
    lightBg: '#FAF5FF',
    hoverBg: '#F3E8FF',
    badgeBg: '#6B46C1',
    iconColor: '#805AD5',
  },
  lab: {
    key: 'lab',
    label: 'AI Native',
    shortLabel: 'AI Native',
    primary: '#0D2B4E',
    secondary: '#0EA5E9',
    gradient: 'linear-gradient(135deg, #0D2B4E 0%, #0EA5E9 100%)',
    lightBg: '#F0F9FF',
    hoverBg: '#E0F2FE',
    badgeBg: '#0EA5E9',
    iconColor: '#0EA5E9',
  },
}

/** Platform-neutral tokens — all domains share these */
export const platformTokens = {
  colorBgLayout: '#F7FAFC',
  colorBgContainer: '#FFFFFF',
  colorBgElevated: '#FFFFFF',
  colorText: '#1A202C',
  colorTextSecondary: '#718096',
  colorTextTertiary: '#A0AEC0',
  colorBorder: '#E2E8F0',
  colorBorderSecondary: '#EDF2F7',
  borderRadius: 10,
  borderRadiusLG: 12,
  borderRadiusSM: 6,
  fontFamily:
    '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, sans-serif',
  fontSize: 14,
  fontSizeLG: 16,
}

/** Build Ant Design ThemeConfig for a given domain */
export function buildAntTheme(domain: Domain = 'academic'): ThemeConfig {
  const dt = domainThemes[domain]
  return {
    token: {
      ...platformTokens,
      colorPrimary: dt.primary,
      colorPrimaryHover: dt.secondary,
      colorPrimaryActive: dt.primary,
      colorLink: dt.primary,
      colorLinkHover: dt.secondary,
      colorSuccess: '#48BB78',
      colorWarning: '#F6AD55',
      colorError: '#F56565',
      colorInfo: dt.secondary,
    },
    components: {
      Layout: {
        headerBg: '#FFFFFF',
        headerHeight: 64,
        headerPadding: '0 24px',
        siderBg: '#FFFFFF',
        triggerBg: '#F7FAFC',
        bodyBg: platformTokens.colorBgLayout,
      },
      Card: {
        borderRadiusLG: 12,
        boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)',
        boxShadowSecondary:
          '0 4px 6px -1px rgba(0,0,0,0.04), 0 2px 4px -1px rgba(0,0,0,0.02)',
        headerBg: 'transparent',
      },
      Table: {
        borderRadius: 8,
        headerBg: '#F8FAFC',
        headerColor: '#4A5568',
        rowHoverBg: '#F7FAFC',
      },
      Menu: {
        itemSelectedBg: dt.lightBg,
        itemSelectedColor: dt.primary,
        itemHoverBg: '#F7FAFC',
        itemHoverColor: dt.primary,
        itemBorderRadius: 8,
      },
      Button: {
        borderRadius: 8,
        primaryShadow: '0 2px 4px rgba(30,58,95,0.12)',
      },
      Input: {
        borderRadius: 10,
        activeShadow: `0 0 0 3px ${dt.primary}18`,
      },
      Segmented: {
        itemSelectedBg: '#FFFFFF',
        itemSelectedColor: dt.primary,
        borderRadius: 10,
      },
      Tag: {
        borderRadius: 6,
      },
      Badge: {
        colorBgContainer: '#FFFFFF',
      },
      Statistic: {
        contentFontSize: 28,
      },
    },
  }
}

/** Semantic color palette — used across all domains */
export const semanticColors = {
  // Status / result colors (Ant Design convention)
  blue: '#1890ff',
  green: '#52c41a',
  gold: '#faad14',
  purple: '#722ed1',
  red: '#ff4d4f',
  cyan: '#13c2c2',
  magenta: '#eb2f96',
  orange: '#fa8c16',

  // Domain-specific accents (opensource domain)
  osGreen: '#38A169',
  osGreenLight: '#48BB78',
  osOrange: '#F6AD55',
  osOrangeDark: '#DD6B20',
  osBlue: '#3182CE',
  osRed: '#E53E3E',
  osPurple: '#805AD5',
  osYellow: '#D69E2E',

  // Neutral / UI chrome
  bgGray: '#f5f5f5',
  bgGrayLight: '#fafafa',
  borderGray: '#d9d9d9',
  borderGrayLight: '#f0f0f0',
  textGray: '#8c8c8c',
  divider: '#E2E8F0',
  hoverBg: '#F7FAFC',

  // Specialty backgrounds
  greenBg: '#f6ffed',
  goldBg: '#fffbe6',
  redBg: '#fff2f0',
  purpleBg: '#f9f0ff',
  blueBg: '#e6f7ff',
} as const

/** CSS variable map for runtime switching without JS re-render */
export function applyDomainCssVars(domain: Domain): void {
  const dt = domainThemes[domain]
  const root = document.documentElement
  // Domain tokens
  root.style.setProperty('--domain-primary', dt.primary)
  root.style.setProperty('--domain-secondary', dt.secondary)
  root.style.setProperty('--domain-gradient', dt.gradient)
  root.style.setProperty('--domain-light-bg', dt.lightBg)
  root.style.setProperty('--domain-hover-bg', dt.hoverBg)
  root.style.setProperty('--domain-badge-bg', dt.badgeBg)
  root.style.setProperty('--domain-icon-color', dt.iconColor)
  // Semantic color tokens (for CSS files)
  root.style.setProperty('--color-blue', semanticColors.blue)
  root.style.setProperty('--color-green', semanticColors.green)
  root.style.setProperty('--color-gold', semanticColors.gold)
  root.style.setProperty('--color-purple', semanticColors.purple)
  root.style.setProperty('--color-red', semanticColors.red)
  root.style.setProperty('--color-cyan', semanticColors.cyan)
  root.style.setProperty('--color-magenta', semanticColors.magenta)
  root.style.setProperty('--color-orange', semanticColors.orange)
  root.style.setProperty('--color-bg-gray', semanticColors.bgGray)
  root.style.setProperty('--color-bg-gray-light', semanticColors.bgGrayLight)
  root.style.setProperty('--color-border-gray', semanticColors.borderGray)
  root.style.setProperty('--color-border-gray-light', semanticColors.borderGrayLight)
  root.style.setProperty('--color-text-gray', semanticColors.textGray)
  root.style.setProperty('--color-divider', semanticColors.divider)
  root.setAttribute('data-domain', domain)
}

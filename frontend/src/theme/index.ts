/**
 * Design System for AI4TALENTS — Multi-Domain Talent Platform
 *
 * Architecture: Neutral platform base + domain-aware tokens.
 * Current active domain: academic (学术人才).
 * Future domains: opensource, competition, industry — slots reserved.
 */

import type { ThemeConfig } from 'antd'

export type Domain = 'academic' | 'opensource' | 'competition' | 'industry'

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

/** CSS variable map for runtime switching without JS re-render */
export function applyDomainCssVars(domain: Domain): void {
  const dt = domainThemes[domain]
  const root = document.documentElement
  root.style.setProperty('--domain-primary', dt.primary)
  root.style.setProperty('--domain-secondary', dt.secondary)
  root.style.setProperty('--domain-gradient', dt.gradient)
  root.style.setProperty('--domain-light-bg', dt.lightBg)
  root.style.setProperty('--domain-hover-bg', dt.hoverBg)
  root.style.setProperty('--domain-badge-bg', dt.badgeBg)
  root.style.setProperty('--domain-icon-color', dt.iconColor)
  root.setAttribute('data-domain', domain)
}

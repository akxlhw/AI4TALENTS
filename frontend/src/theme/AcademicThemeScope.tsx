import React from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { buildAntTheme, domainThemes } from './index'

/**
 * Pins the academic domain theme for standalone pages (login/register).
 *
 * The global theme (AntD tokens + --domain-* CSS variables) follows the
 * user's currently selected domain, which made the login page change color
 * after the user switched domains. This scope overrides both — a nested
 * ConfigProvider with the academic theme, and the academic CSS variables on
 * a wrapper div (custom properties cascade, so descendants always see the
 * academic values without touching the document-level variables or the
 * user's domain choice).
 */
const AcademicThemeScope: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dt = domainThemes.academic
  const scopedVars = {
    '--domain-primary': dt.primary,
    '--domain-secondary': dt.secondary,
    '--domain-gradient': dt.gradient,
    '--domain-light-bg': dt.lightBg,
    '--domain-hover-bg': dt.hoverBg,
    '--domain-badge-bg': dt.badgeBg,
    '--domain-icon-color': dt.iconColor,
  } as React.CSSProperties

  return (
    <ConfigProvider locale={zhCN} theme={buildAntTheme('academic')}>
      <div style={scopedVars}>{children}</div>
    </ConfigProvider>
  )
}

export default AcademicThemeScope

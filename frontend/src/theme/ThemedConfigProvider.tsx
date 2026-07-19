import React, { useMemo } from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useDomainStore } from '../stores/domainStore'
import { buildAntTheme } from './index'

// Rebuild the AntD theme whenever the domain changes so component-level
// tokens (primary color, links, menu selection) follow the active domain —
// previously the theme was computed once at startup and switching domains
// only updated the CSS variables, leaving AntD components stuck on academic.
const ThemedConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const currentDomain = useDomainStore((s) => s.currentDomain)
  const theme = useMemo(() => buildAntTheme(currentDomain), [currentDomain])
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      {children}
    </ConfigProvider>
  )
}

export default ThemedConfigProvider

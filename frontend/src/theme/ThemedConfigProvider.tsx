import React, { useMemo } from 'react'
import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import { useTranslation } from 'react-i18next'
import { useDomainStore } from '../stores/domainStore'
import { buildAntTheme } from './index'

// Rebuild the AntD theme whenever the domain changes so component-level
// tokens (primary color, links, menu selection) follow the active domain —
// previously the theme was computed once at startup and switching domains
// only updated the CSS variables, leaving AntD components stuck on academic.
const ThemedConfigProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const currentDomain = useDomainStore((s) => s.currentDomain)
  const { i18n } = useTranslation()
  const theme = useMemo(() => buildAntTheme(currentDomain), [currentDomain])
  const locale = i18n.language === 'en' ? enUS : zhCN
  return (
    <ConfigProvider locale={locale} theme={theme}>
      {children}
    </ConfigProvider>
  )
}

export default ThemedConfigProvider

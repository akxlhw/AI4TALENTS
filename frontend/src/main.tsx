import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { QueryClientProvider } from '@tanstack/react-query'
import zhCN from 'antd/locale/zh_CN'
import { queryClient } from './hooks/queryClient'
import { useDomainStore } from './stores/domainStore'
import { buildAntTheme } from './theme'
import App from './App'
import './index.css'

// Initialize domain CSS variables before first render
const initialDomain = useDomainStore.getState().currentDomain

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={buildAntTheme(initialDomain)}>
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

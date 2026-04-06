import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { QueryClientProvider } from '@tanstack/react-query'
import zhCN from 'antd/locale/zh_CN'
import { queryClient } from './hooks/queryClient'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

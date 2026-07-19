import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './hooks/queryClient'
import ThemedConfigProvider from './theme/ThemedConfigProvider'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemedConfigProvider>
        <App />
      </ThemedConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

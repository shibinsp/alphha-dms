import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

// Ant Design theme configuration
const theme = {
  token: {
    colorPrimary: '#1E3A5F',
    colorSuccess: '#388E3C',
    colorWarning: '#FFA000',
    colorError: '#D32F2F',
    colorInfo: '#1E3A5F',
    fontFamily: 'Inter, Roboto, sans-serif',
    borderRadius: 6,
  },
  components: {
    Layout: {
      headerBg: '#1E3A5F',
      siderBg: '#FFFFFF',
    },
    Menu: {
      itemSelectedBg: '#E8EDF3',
      itemSelectedColor: '#1E3A5F',
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={theme}>
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

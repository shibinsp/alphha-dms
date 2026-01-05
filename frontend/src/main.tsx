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

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope)

        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                console.log('New version available!')
                // Could show update notification here
              }
            })
          }
        })
      })
      .catch((error) => {
        console.error('SW registration failed:', error)
      })

    // Listen for messages from service worker
    navigator.serviceWorker.addEventListener('message', (event) => {
      const { type, ...data } = event.data
      switch (type) {
        case 'SYNC_SUCCESS':
          console.log('Sync completed:', data)
          // Could trigger a refetch or show notification
          break
        case 'DOCUMENT_CACHED':
          console.log('Document cached:', data.documentId)
          break
      }
    })
  })
}

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

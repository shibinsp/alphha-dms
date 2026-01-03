import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Spin, message } from 'antd'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'

// Layouts
import MainLayout from '@/layouts/MainLayout'
import AuthLayout from '@/layouts/AuthLayout'

// Pages
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import DocumentListPage from '@/pages/documents/DocumentListPage'
import DocumentDetailPage from '@/pages/documents/DocumentDetailPage'
import DocumentUploadPage from '@/pages/documents/DocumentUploadPage'
import ApprovalQueuePage from '@/pages/approvals/ApprovalQueuePage'
import LegalHoldsPage from '@/pages/compliance/LegalHoldsPage'
import PIISettingsPage from '@/pages/settings/PIISettingsPage'
import SearchPage from '@/pages/search/SearchPage'
import ChatPage from '@/pages/chat/ChatPage'
// Phase 4 Pages
import AnalyticsDashboard from '@/pages/analytics/AnalyticsDashboard'
import BSIAnalysisPage from '@/pages/bsi/BSIAnalysisPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spin size="large" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function SessionExpiredHandler() {
  const navigate = useNavigate()

  useEffect(() => {
    const handleSessionExpired = () => {
      message.error('Session expired. Please login again.')
      navigate('/login', { replace: true })
    }

    window.addEventListener('session-expired', handleSessionExpired)
    return () => window.removeEventListener('session-expired', handleSessionExpired)
  }, [navigate])

  return null
}

function App() {
  const { accessToken, setLoading, login, logout } = useAuthStore()

  useEffect(() => {
    const initAuth = async () => {
      if (accessToken) {
        try {
          const user = await authService.getCurrentUser()
          login(user, {
            access_token: accessToken,
            refresh_token: useAuthStore.getState().refreshToken || '',
            token_type: 'bearer',
          })
        } catch {
          logout()
        }
      } else {
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  return (
    <BrowserRouter>
      <SessionExpiredHandler />
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <AuthLayout>
                <LoginPage />
              </AuthLayout>
            </PublicRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="documents" element={<DocumentListPage />} />
          <Route path="documents/upload" element={<DocumentUploadPage />} />
          <Route path="documents/:id" element={<DocumentDetailPage />} />
          <Route path="approvals" element={<ApprovalQueuePage />} />
          <Route path="compliance/legal-holds" element={<LegalHoldsPage />} />
          <Route path="settings/pii" element={<PIISettingsPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="chat" element={<ChatPage />} />
          {/* Phase 4 Routes */}
          <Route path="analytics" element={<AnalyticsDashboard />} />
          <Route path="bsi" element={<BSIAnalysisPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

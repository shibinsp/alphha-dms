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
import DocumentOverviewPage from '@/pages/documents/DocumentOverviewPage'
import DocumentDashboard from '@/pages/documents/DocumentDashboard'
import ApprovalQueuePage from '@/pages/approvals/ApprovalQueuePage'
import LegalHoldsPage from '@/pages/compliance/LegalHoldsPage'
import RetentionPoliciesPage from '@/pages/compliance/RetentionPoliciesPage'
import AuditLogPage from '@/pages/compliance/AuditLogPage'
import PIISettingsPage from '@/pages/settings/PIISettingsPage'
import WorkflowsPage from '@/pages/settings/WorkflowsPage'
import SearchPage from '@/pages/search/SearchPage'
import ChatPage from '@/pages/chat/ChatPage'
// Phase 4 Pages
import AnalyticsDashboard from '@/pages/analytics/AnalyticsDashboard'
import BSIAnalysisPage from '@/pages/bsi/BSIAnalysisPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
// Admin Pages
import UsersPage from '@/pages/admin/UsersPage'
import RolesPage from '@/pages/admin/RolesPage'
import DocumentTypesPage from '@/pages/admin/DocumentTypesPage'
import SettingsPage from '@/pages/admin/SettingsPage'
// Entity Pages
import CustomersPage from '@/pages/entities/CustomersPage'
import VendorsPage from '@/pages/entities/VendorsPage'
import DepartmentsPage from '@/pages/entities/DepartmentsPage'

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
          <Route path="compliance/retention" element={<RetentionPoliciesPage />} />
          <Route path="compliance/audit" element={<AuditLogPage />} />
          <Route path="settings/pii" element={<PIISettingsPage />} />
          <Route path="settings/workflows" element={<WorkflowsPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="chat" element={<ChatPage />} />
          {/* Phase 4 Routes */}
          <Route path="analytics" element={<AnalyticsDashboard />} />
          <Route path="bsi" element={<BSIAnalysisPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          {/* Admin Routes */}
          <Route path="admin/users" element={<UsersPage />} />
          <Route path="admin/roles" element={<RolesPage />} />
          <Route path="admin/document-types" element={<DocumentTypesPage />} />
          <Route path="admin/settings" element={<SettingsPage />} />
          {/* Entity Routes */}
          <Route path="entities/customers" element={<CustomersPage />} />
          <Route path="entities/vendors" element={<VendorsPage />} />
          <Route path="entities/departments" element={<DepartmentsPage />} />
          {/* Document Routes */}
          <Route path="documents/dashboard" element={<DocumentDashboard />} />
          <Route path="documents/:id/overview" element={<DocumentOverviewPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

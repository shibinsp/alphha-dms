import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Spin, App as AntApp } from 'antd'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'

// Layouts
import MainLayout from '@/layouts/MainLayout'
import AuthLayout from '@/layouts/AuthLayout'

// Pages
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import DocumentListPage from '@/pages/documents/DocumentListPage'
import DocumentDetailPage from '@/pages/documents/DocumentDetailPage'
import DocumentUploadPage from '@/pages/documents/DocumentUploadPage'
import DocumentOverviewPage from '@/pages/documents/DocumentOverviewPage'
import DocumentDashboard from '@/pages/documents/DocumentDashboard'
import DocumentEditPage from '@/pages/documents/DocumentEditPage'
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
// Access Requests
import AccessRequestsPage from '@/pages/access-requests/AccessRequestsPage'

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

// Helper to check if user has required permission
function hasPermission(user: { roles: { permissions: string[] }[] } | null, permission: string): boolean {
  if (!user) return false
  
  // Check if user has the exact permission or a wildcard that covers it
  return user.roles.some(role => {
    // Super admin has all permissions
    if (role.permissions.includes('*')) return true
    
    // Check exact match
    if (role.permissions.includes(permission)) return true
    
    // Check wildcard match (e.g., 'documents:*' covers 'documents:read')
    const [category] = permission.split('.')
    const [permCategory] = permission.split(':')
    
    // Check category wildcard (e.g., 'admin:*' covers 'admin.users')
    if (role.permissions.includes(`${category}:*`)) return true
    if (role.permissions.includes(`${permCategory}:*`)) return true
    
    // Special case: workflows:approve should grant approvals.view
    if (permission === 'approvals.view' && role.permissions.includes('workflows:approve')) return true
    
    // Special case: admin:* should grant all admin permissions
    if (permission.startsWith('admin.') && role.permissions.includes('admin:*')) return true
    
    // Special case: analytics:view permission
    if (permission === 'analytics.view' && role.permissions.includes('analytics:view')) return true
    
    return false
  })
}

// Route that requires specific permission
function RequirePermission({ children, permission }: { children: React.ReactNode; permission: string }) {
  const { user } = useAuthStore()
  
  if (!hasPermission(user, permission)) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8">
        <div className="text-6xl mb-4">🔒</div>
        <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
        <p className="text-gray-500 mb-4">You don't have permission to access this page.</p>
        <a href="/" className="text-blue-500 hover:underline">Return to Dashboard</a>
      </div>
    )
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
        <Route
          path="/register"
          element={
            <PublicRoute>
              <AuthLayout>
                <RegisterPage />
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
          <Route path="documents/:id/edit" element={<DocumentEditPage />} />
          <Route path="approvals" element={<RequirePermission permission="approvals.view"><ApprovalQueuePage /></RequirePermission>} />
          <Route path="workflows" element={<RequirePermission permission="admin.workflows"><WorkflowsPage /></RequirePermission>} />
          <Route path="compliance/legal-holds" element={<RequirePermission permission="compliance.legal_holds"><LegalHoldsPage /></RequirePermission>} />
          <Route path="compliance/retention" element={<RequirePermission permission="compliance.retention"><RetentionPoliciesPage /></RequirePermission>} />
          <Route path="compliance/audit" element={<RequirePermission permission="compliance.audit"><AuditLogPage /></RequirePermission>} />
          <Route path="settings/pii" element={<RequirePermission permission="admin.pii"><PIISettingsPage /></RequirePermission>} />
          <Route path="settings/workflows" element={<RequirePermission permission="admin.workflows"><WorkflowsPage /></RequirePermission>} />
          <Route path="search" element={<SearchPage />} />
          <Route path="chat" element={<RequirePermission permission="ai.chat"><ChatPage /></RequirePermission>} />
          {/* Phase 4 Routes */}
          <Route path="analytics" element={<RequirePermission permission="analytics.view"><AnalyticsDashboard /></RequirePermission>} />
          <Route path="bsi" element={<RequirePermission permission="bsi.view"><BSIAnalysisPage /></RequirePermission>} />
          <Route path="notifications" element={<NotificationsPage />} />
          {/* Admin Routes */}
          <Route path="admin/users" element={<RequirePermission permission="admin.users"><UsersPage /></RequirePermission>} />
          <Route path="admin/roles" element={<RequirePermission permission="admin.roles"><RolesPage /></RequirePermission>} />
          <Route path="admin/document-types" element={<RequirePermission permission="admin.document_types"><DocumentTypesPage /></RequirePermission>} />
          <Route path="admin/settings" element={<RequirePermission permission="admin.settings"><SettingsPage /></RequirePermission>} />
          {/* Entity Routes */}
          <Route path="entities/customers" element={<RequirePermission permission="entities.view"><CustomersPage /></RequirePermission>} />
          <Route path="entities/vendors" element={<RequirePermission permission="entities.view"><VendorsPage /></RequirePermission>} />
          <Route path="entities/departments" element={<RequirePermission permission="entities.view"><DepartmentsPage /></RequirePermission>} />
          {/* Access Requests */}
          <Route path="access-requests" element={<AccessRequestsPage />} />
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

// Wrap with AntApp for message/notification context
const AppWrapper = () => (
  <AntApp>
    <App />
  </AntApp>
)

export default AppWrapper

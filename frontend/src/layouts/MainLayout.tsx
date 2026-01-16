import React, { useState, useMemo } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Badge,
  Button,
  theme,
} from 'antd'
import {
  DashboardOutlined,
  FileOutlined,
  UploadOutlined,
  SearchOutlined,
  TeamOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  AuditOutlined,
  SafetyOutlined,
  RobotOutlined,
  BarChartOutlined,
  BankOutlined,
  ShopOutlined,
  FolderOutlined,
  TableOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'
import api from '@/services/api'

const { Header, Sider, Content } = Layout

// Permission checker helper
const hasPermission = (userPermissions: string[], required: string[]): boolean => {
  if (userPermissions.includes('*')) return true;
  return required.some(req => 
    userPermissions.some(p => p === req || p === `${req.split(':')[0]}:*` || p.startsWith(req.split(':')[0] + ':'))
  );
};

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, refreshToken } = useAuthStore()

  const { data: unreadData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => {
      const { data } = await api.get('/notifications/unread-count')
      return data
    },
    refetchInterval: 30000,
  })
  const unreadCount = unreadData?.unread_count || 0
  const { token } = theme.useToken()

  // Get user permissions from roles
  const userPermissions = useMemo(() => {
    if (!user?.roles) return [];
    return user.roles.flatMap(r => r.permissions || []);
  }, [user]);

  const userRoles = useMemo(() => {
    if (!user?.roles) return [];
    return user.roles.map(r => r.name);
  }, [user]);

  const isAdmin = userRoles.includes('super_admin') || userRoles.includes('admin');
  const isManager = userRoles.includes('manager');
  const isLegal = userRoles.includes('legal');
  const isCompliance = userRoles.includes('compliance');
  const isViewer = userRoles.includes('viewer');
  const canManageDocuments = hasPermission(userPermissions, ['documents:create', 'documents:update']);
  const canViewAnalytics = hasPermission(userPermissions, ['analytics:view']) || isAdmin || isManager;
  const canApprove = hasPermission(userPermissions, ['workflows:approve']) || isAdmin || isManager;
  const canAccessCompliance = isAdmin || isLegal || isCompliance;

  const handleLogout = async () => {
    if (refreshToken) {
      try {
        await authService.logout(refreshToken)
      } catch {
        // Continue with logout even if API fails
      }
    }
    logout()
    navigate('/login')
  }

  const menuItems = useMemo(() => {
    const items: any[] = [
      {
        key: '/',
        icon: <DashboardOutlined />,
        label: 'Dashboard',
      },
      {
        key: 'documents-menu',
        icon: <FileOutlined />,
        label: 'Documents',
        children: [
          { key: '/documents', icon: <FileOutlined />, label: 'All Documents' },
          { key: '/documents/dashboard', icon: <TableOutlined />, label: 'Document Dashboard' },
          ...(canManageDocuments ? [{ key: '/documents/upload', icon: <UploadOutlined />, label: 'Upload' }] : []),
        ],
      },
    ];

    // Entities - Admin, Manager only
    if (isAdmin || isManager) {
      items.push({
        key: 'entities-menu',
        icon: <UserOutlined />,
        label: 'Entities',
        children: [
          { key: '/entities/customers', icon: <UserOutlined />, label: 'Customers' },
          { key: '/entities/vendors', icon: <ShopOutlined />, label: 'Vendors' },
          { key: '/entities/departments', icon: <BankOutlined />, label: 'Departments' },
        ],
      });
    }

    // Search - Everyone
    items.push({ key: '/search', icon: <SearchOutlined />, label: 'Search' });

    // AI Chat - Everyone except viewer
    if (!isViewer) {
      items.push({ key: '/chat', icon: <RobotOutlined />, label: 'AI Chat' });
    }

    // Analytics - Admin, Manager
    if (canViewAnalytics) {
      items.push({ key: '/analytics', icon: <BarChartOutlined />, label: 'Analytics' });
    }

    // Bank Statements - Admin, Manager, Compliance
    if (isAdmin || isManager || isCompliance) {
      items.push({ key: '/bsi', icon: <BankOutlined />, label: 'Bank Statements' });
    }

    // Approvals - Admin, Manager
    if (canApprove) {
      items.push({
        key: 'approvals-menu',
        icon: <AuditOutlined />,
        label: 'Document Approvals',
        children: [
          { key: '/approvals', label: 'Pending Approvals' },
          { key: '/workflows', label: 'Workflows' },
        ]
      });
    }

    // Access Requests - Everyone (for requesting access to restricted documents)
    items.push({ key: '/access-requests', icon: <SafetyOutlined />, label: 'Access Requests' });

    // Compliance - Admin, Legal, Compliance
    if (canAccessCompliance) {
      items.push({
        key: 'compliance',
        icon: <SafetyOutlined />,
        label: 'Compliance',
        children: [
          { key: '/compliance/legal-holds', icon: <SafetyOutlined />, label: 'Legal Holds' },
          { key: '/compliance/retention', icon: <AuditOutlined />, label: 'Retention Policies' },
          { key: '/compliance/audit', icon: <AuditOutlined />, label: 'Audit Log' },
        ],
      });
    }

    // Administration - Admin only
    if (isAdmin) {
      items.push({
        key: 'admin',
        icon: <SettingOutlined />,
        label: 'Administration',
        children: [
          { key: '/admin/users', icon: <TeamOutlined />, label: 'Users' },
          { key: '/admin/roles', icon: <SafetyOutlined />, label: 'Roles' },
          { key: '/admin/document-types', icon: <FolderOutlined />, label: 'Document Types' },
          { key: '/admin/settings', icon: <SettingOutlined />, label: 'System Settings' },
          { key: '/settings/pii', icon: <SafetyOutlined />, label: 'PII Detection' },
          { key: '/settings/workflows', icon: <SettingOutlined />, label: 'Workflows' },
        ],
      });
    }

    return items;
  }, [userPermissions, isAdmin, isManager, isLegal, isCompliance, isViewer, canManageDocuments, canViewAnalytics, canApprove, canAccessCompliance]);

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={250}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: token.colorBgContainer,
        }}
      >
        {/* Logo */}
        <div
          className="h-16 flex items-center justify-center border-b"
          style={{ borderColor: token.colorBorderSecondary }}
        >
          <h1
            className={`font-heading font-bold text-primary-500 transition-all ${
              collapsed ? 'text-lg' : 'text-xl'
            }`}
          >
            {collapsed ? 'AD' : 'Alphha DMS'}
          </h1>
        </div>

        {/* Menu */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={['admin']}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>

      {/* Main Layout */}
      <Layout style={{ marginLeft: collapsed ? 80 : 250, transition: 'margin-left 0.2s' }}>
        {/* Header */}
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          {/* Left side */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 48, height: 48 }}
          />

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <Badge count={unreadCount} size="small">
              <Button
                type="text"
                icon={<BellOutlined style={{ fontSize: 18 }} />}
                onClick={() => navigate('/notifications')}
              />
            </Badge>

            {/* User menu */}
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              trigger={['click']}
            >
              <div className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 rounded-lg px-3 py-1">
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  src={user?.avatar_url}
                  style={{ backgroundColor: token.colorPrimary }}
                />
                <span className="text-sm font-medium hidden md:inline">
                  {user?.full_name}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* Content */}
        <Content
          style={{
            margin: 24,
            padding: 24,
            minHeight: 280,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout

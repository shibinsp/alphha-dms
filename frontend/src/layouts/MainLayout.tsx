import React, { useState } from 'react'
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
} from '@ant-design/icons'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'

const { Header, Sider, Content } = Layout

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, refreshToken } = useAuthStore()
  const { token } = theme.useToken()

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

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/documents',
      icon: <FileOutlined />,
      label: 'Documents',
    },
    {
      key: '/documents/upload',
      icon: <UploadOutlined />,
      label: 'Upload',
    },
    {
      key: '/search',
      icon: <SearchOutlined />,
      label: 'Search',
    },
    {
      key: '/chat',
      icon: <RobotOutlined />,
      label: 'AI Chat',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
    {
      key: '/bsi',
      icon: <BankOutlined />,
      label: 'Bank Statements',
    },
    {
      key: '/approvals',
      icon: <AuditOutlined />,
      label: 'Approvals',
    },
    {
      key: 'compliance',
      icon: <SafetyOutlined />,
      label: 'Compliance',
      children: [
        {
          key: '/compliance/legal-holds',
          icon: <SafetyOutlined />,
          label: 'Legal Holds',
        },
        {
          key: '/compliance/retention',
          icon: <AuditOutlined />,
          label: 'Retention Policies',
        },
        {
          key: '/compliance/audit',
          icon: <AuditOutlined />,
          label: 'Audit Log',
        },
      ],
    },
    {
      key: 'admin',
      icon: <SettingOutlined />,
      label: 'Administration',
      children: [
        {
          key: '/admin/users',
          icon: <TeamOutlined />,
          label: 'Users',
        },
        {
          key: '/admin/roles',
          icon: <SafetyOutlined />,
          label: 'Roles',
        },
        {
          key: '/settings/pii',
          icon: <SafetyOutlined />,
          label: 'PII Detection',
        },
        {
          key: '/settings/workflows',
          icon: <SettingOutlined />,
          label: 'Workflows',
        },
      ],
    },
  ]

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
            <Badge count={5} size="small">
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

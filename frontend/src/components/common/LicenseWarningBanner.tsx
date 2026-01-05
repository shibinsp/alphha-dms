import React, { useState, useEffect } from 'react'
import { Alert, Button, Space, Typography } from 'antd'
import { WarningOutlined, ClockCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

const { Text } = Typography

interface LicenseStatus {
  status: 'valid' | 'expiring_soon' | 'grace_period' | 'expired'
  daysRemaining?: number
  warning?: string
}

const LicenseWarningBanner: React.FC = () => {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const navigate = useNavigate()
  const { user } = useAuthStore()

  // Check for license warnings from API responses
  useEffect(() => {
    // Intercept API responses to check for license headers
    const originalFetch = window.fetch
    window.fetch = async (...args) => {
      const response = await originalFetch(...args)

      // Check license headers
      const licenseWarning = response.headers.get('X-License-Warning')
      const licenseStatus = response.headers.get('X-License-Status')
      const daysRemaining = response.headers.get('X-License-Days-Remaining')

      if (licenseStatus && licenseStatus !== 'valid') {
        setLicenseStatus({
          status: licenseStatus as LicenseStatus['status'],
          daysRemaining: daysRemaining ? parseInt(daysRemaining) : undefined,
          warning: licenseWarning || undefined,
        })
      }

      return response
    }

    return () => {
      window.fetch = originalFetch
    }
  }, [])

  // Don't show if dismissed or no warning
  if (dismissed || !licenseStatus || licenseStatus.status === 'valid') {
    return null
  }

  // Only show to admin users
  const isAdmin = user?.roles?.some(r => r.name === 'admin' || r.name === 'super_admin') || user?.is_superuser
  if (!isAdmin) {
    return null
  }

  // Determine alert type and message
  const getAlertProps = () => {
    switch (licenseStatus.status) {
      case 'grace_period':
        return {
          type: 'error' as const,
          icon: <ExclamationCircleOutlined />,
          message: 'License Expired - Grace Period Active',
          description: (
            <Space direction="vertical" size={4}>
              <Text>
                Your license has expired. You are currently in the grace period.
                Please renew your license to avoid service interruption.
              </Text>
              <Text type="secondary">
                {licenseStatus.warning || 'Contact support to renew your license.'}
              </Text>
            </Space>
          ),
        }

      case 'expiring_soon':
        return {
          type: 'warning' as const,
          icon: <WarningOutlined />,
          message: `License Expiring Soon - ${licenseStatus.daysRemaining} Days Remaining`,
          description: (
            <Space direction="vertical" size={4}>
              <Text>
                Your license will expire in {licenseStatus.daysRemaining} days.
                Renew now to ensure uninterrupted service.
              </Text>
            </Space>
          ),
        }

      case 'expired':
        return {
          type: 'error' as const,
          icon: <ClockCircleOutlined />,
          message: 'License Expired',
          description: (
            <Space direction="vertical" size={4}>
              <Text>
                Your license has expired and the grace period has ended.
                Some features may be restricted. Please contact support to renew.
              </Text>
            </Space>
          ),
        }

      default:
        return null
    }
  }

  const alertProps = getAlertProps()
  if (!alertProps) return null

  return (
    <Alert
      {...alertProps}
      banner
      closable={licenseStatus.status === 'expiring_soon'}
      onClose={() => setDismissed(true)}
      action={
        <Space>
          <Button size="small" type="primary" onClick={() => navigate('/admin/license')}>
            Manage License
          </Button>
          <Button size="small" onClick={() => window.open('mailto:support@alphha.io')}>
            Contact Support
          </Button>
        </Space>
      }
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1000,
      }}
    />
  )
}

export default LicenseWarningBanner

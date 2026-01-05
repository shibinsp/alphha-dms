import React, { useState } from 'react'
import {
  Card,
  Typography,
  Descriptions,
  Tag,
  Button,
  Space,
  Progress,
  Alert,
  Input,
  message,
  Modal,
  Divider,
  Row,
  Col,
  Statistic,
  Timeline,
} from 'antd'
import {
  SafetyCertificateOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  KeyOutlined,
  ReloadOutlined,
  CopyOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text, Paragraph } = Typography

interface License {
  id: string
  license_key: string
  tenant_id: string
  expires_at: string
  grace_period_days: number
  is_active: boolean
  is_tampered: boolean
  last_validated_at: string
  created_at: string
}

interface LicenseValidation {
  is_valid: boolean
  message: string
  expires_at: string
  days_remaining: number
  in_grace_period: boolean
}

const LicensePage: React.FC = () => {
  const queryClient = useQueryClient()
  const [renewModalOpen, setRenewModalOpen] = useState(false)
  const [newLicenseKey, setNewLicenseKey] = useState('')

  // Fetch license info
  const { data: license, isLoading } = useQuery<License>({
    queryKey: ['license'],
    queryFn: async () => {
      const response = await api.get('/license')
      return response.data
    },
    retry: false,
  })

  // Validate license
  const { data: validation } = useQuery<LicenseValidation>({
    queryKey: ['license-validation'],
    queryFn: async () => {
      const response = await api.get('/license/validate')
      return response.data
    },
    enabled: !!license,
  })

  // Renew license mutation
  const renewMutation = useMutation({
    mutationFn: async (licenseKey: string) => {
      const response = await api.post('/license/renew', { license_key: licenseKey })
      return response.data
    },
    onSuccess: () => {
      message.success('License renewed successfully')
      queryClient.invalidateQueries({ queryKey: ['license'] })
      queryClient.invalidateQueries({ queryKey: ['license-validation'] })
      setRenewModalOpen(false)
      setNewLicenseKey('')
    },
    onError: () => {
      message.error('Failed to renew license')
    },
  })

  // Calculate days until expiry
  const getDaysRemaining = () => {
    if (!license?.expires_at) return 0
    return dayjs(license.expires_at).diff(dayjs(), 'day')
  }

  // Get status info
  const getStatusInfo = () => {
    if (!license) {
      return {
        color: 'error' as const,
        text: 'No License',
        icon: <ExclamationCircleOutlined />,
      }
    }

    if (license.is_tampered) {
      return {
        color: 'error' as const,
        text: 'Tampered',
        icon: <ExclamationCircleOutlined />,
      }
    }

    if (!license.is_active) {
      return {
        color: 'error' as const,
        text: 'Inactive',
        icon: <ClockCircleOutlined />,
      }
    }

    const daysRemaining = getDaysRemaining()

    if (daysRemaining < 0) {
      return {
        color: 'error' as const,
        text: 'Expired',
        icon: <ExclamationCircleOutlined />,
      }
    }

    if (daysRemaining <= 30) {
      return {
        color: 'warning' as const,
        text: 'Expiring Soon',
        icon: <ClockCircleOutlined />,
      }
    }

    return {
      color: 'success' as const,
      text: 'Active',
      icon: <CheckCircleOutlined />,
    }
  }

  const statusInfo = getStatusInfo()
  const daysRemaining = getDaysRemaining()

  // Copy license key
  const handleCopyKey = () => {
    if (license?.license_key) {
      navigator.clipboard.writeText(license.license_key)
      message.success('License key copied to clipboard')
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <Title level={2}>
          <SafetyCertificateOutlined className="mr-2" />
          License Management
        </Title>
        <Text type="secondary">
          Manage your Alphha DMS license and subscription
        </Text>
      </div>

      {/* Warning Alert */}
      {validation?.in_grace_period && (
        <Alert
          type="error"
          icon={<ExclamationCircleOutlined />}
          message="License Expired - Grace Period Active"
          description="Your license has expired. Please renew immediately to avoid service interruption."
          showIcon
          className="mb-6"
          action={
            <Button danger onClick={() => setRenewModalOpen(true)}>
              Renew Now
            </Button>
          }
        />
      )}

      {daysRemaining > 0 && daysRemaining <= 30 && !validation?.in_grace_period && (
        <Alert
          type="warning"
          icon={<ClockCircleOutlined />}
          message={`License Expiring in ${daysRemaining} Days`}
          description="Your license will expire soon. Consider renewing to ensure uninterrupted service."
          showIcon
          className="mb-6"
        />
      )}

      <Row gutter={[24, 24]}>
        {/* License Status Card */}
        <Col xs={24} lg={16}>
          <Card loading={isLoading}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <Title level={4} className="mb-0">License Details</Title>
                <Text type="secondary">Your current license information</Text>
              </div>
              <Tag
                icon={statusInfo.icon}
                color={statusInfo.color}
                style={{ fontSize: 14, padding: '4px 12px' }}
              >
                {statusInfo.text}
              </Tag>
            </div>

            <Descriptions column={{ xs: 1, sm: 2 }} bordered>
              <Descriptions.Item label="License Key">
                <Space>
                  <Text code>
                    {license?.license_key
                      ? `${license.license_key.slice(0, 15)}...`
                      : 'N/A'}
                  </Text>
                  {license?.license_key && (
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={handleCopyKey}
                    />
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Expires At">
                {license?.expires_at
                  ? dayjs(license.expires_at).format('MMMM D, YYYY')
                  : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Days Remaining">
                {daysRemaining > 0 ? (
                  <Text strong>{daysRemaining} days</Text>
                ) : (
                  <Text type="danger">Expired</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Grace Period">
                {license?.grace_period_days} days
              </Descriptions.Item>
              <Descriptions.Item label="Last Validated">
                {license?.last_validated_at
                  ? dayjs(license.last_validated_at).format('MMM D, YYYY h:mm A')
                  : 'Never'}
              </Descriptions.Item>
            </Descriptions>

            {/* Validity Progress */}
            {license && (
              <div className="mt-6">
                <Text type="secondary" className="block mb-2">
                  License Validity
                </Text>
                <Progress
                  percent={Math.max(0, Math.min(100, (daysRemaining / 365) * 100))}
                  status={daysRemaining <= 30 ? 'exception' : 'active'}
                  strokeColor={
                    daysRemaining <= 0
                      ? '#ff4d4f'
                      : daysRemaining <= 30
                      ? '#faad14'
                      : '#52c41a'
                  }
                  format={() => `${daysRemaining} days`}
                />
              </div>
            )}

            <Divider />

            <Space>
              <Button
                type="primary"
                icon={<KeyOutlined />}
                onClick={() => setRenewModalOpen(true)}
              >
                Renew License
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['license'] })}
              >
                Refresh
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Stats and Info */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* Quick Stats */}
            <Card>
              <Statistic
                title="Days Remaining"
                value={Math.max(0, daysRemaining)}
                prefix={<ClockCircleOutlined />}
                valueStyle={{
                  color: daysRemaining <= 30 ? '#ff4d4f' : '#52c41a',
                }}
              />
            </Card>

            {/* Support Info */}
            <Card>
              <Title level={5}>Need Help?</Title>
              <Paragraph type="secondary">
                Contact our support team for license-related inquiries or to purchase a renewal.
              </Paragraph>
              <Space direction="vertical">
                <Button block onClick={() => window.open('mailto:support@alphha.io')}>
                  Email Support
                </Button>
                <Button block type="link" onClick={() => window.open('https://alphha.io/pricing')}>
                  View Pricing
                </Button>
              </Space>
            </Card>

            {/* License History */}
            <Card title="Recent Activity">
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <>
                        <Text strong>License Validated</Text>
                        <br />
                        <Text type="secondary">
                          {license?.last_validated_at
                            ? dayjs(license.last_validated_at).fromNow()
                            : 'Never'}
                        </Text>
                      </>
                    ),
                  },
                  {
                    color: 'blue',
                    children: (
                      <>
                        <Text strong>License Created</Text>
                        <br />
                        <Text type="secondary">
                          {license?.created_at
                            ? dayjs(license.created_at).format('MMM D, YYYY')
                            : 'Unknown'}
                        </Text>
                      </>
                    ),
                  },
                ]}
              />
            </Card>
          </Space>
        </Col>
      </Row>

      {/* Renew Modal */}
      <Modal
        title="Renew License"
        open={renewModalOpen}
        onCancel={() => {
          setRenewModalOpen(false)
          setNewLicenseKey('')
        }}
        footer={[
          <Button key="cancel" onClick={() => setRenewModalOpen(false)}>
            Cancel
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={renewMutation.isPending}
            onClick={() => renewMutation.mutate(newLicenseKey)}
            disabled={!newLicenseKey}
          >
            Activate License
          </Button>,
        ]}
      >
        <Paragraph>
          Enter your new license key below to renew your subscription.
          Contact <a href="mailto:sales@alphha.io">sales@alphha.io</a> to purchase a license key.
        </Paragraph>
        <Input.TextArea
          placeholder="ADMS-XXXX-XXXX-XXXX-XXXX"
          value={newLicenseKey}
          onChange={(e) => setNewLicenseKey(e.target.value)}
          rows={3}
          style={{ fontFamily: 'monospace' }}
        />
      </Modal>
    </div>
  )
}

export default LicensePage

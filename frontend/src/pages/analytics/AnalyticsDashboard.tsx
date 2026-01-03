import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Typography,
  Tabs,
  Spin,
  Alert,
  Space,
  Button,
  DatePicker,
} from 'antd'
import {
  FileOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CloudOutlined,
  SafetyOutlined,
  ArrowUpOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { api } from '@/services/api'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

interface DashboardStats {
  documents: {
    total_documents: number
    documents_today: number
    documents_this_week: number
    documents_this_month: number
    by_status: Record<string, number>
    by_type: Record<string, number>
    by_department: Record<string, number>
  }
  ocr: {
    total_processed: number
    pending: number
    failed: number
    avg_processing_time: number
    success_rate: number
  }
  workflows: {
    pending_approvals: number
    approved_today: number
    rejected_today: number
    avg_approval_time: number
    overdue_count: number
  }
  compliance: {
    compliance_score: number
    documents_with_pii: number
    legal_holds_active: number
    retention_expiring_soon: number
    worm_records: number
  }
  storage: {
    total_storage_mb: number
    used_storage_mb: number
    storage_by_type: Record<string, number>
  }
  recent_activity: Array<{
    id: string
    event_type: string
    entity_type: string
    created_at: string
  }>
  alerts: Array<{
    id: string
    alert_type: string
    severity: string
    title: string
    created_at: string
  }>
}

const AnalyticsDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview')

  const { data: stats, isLoading, error, refetch } = useQuery<DashboardStats>({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      const response = await api.get('/analytics/dashboard')
      return response.data
    },
    refetchInterval: 60000, // Refresh every minute
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" tip="Loading dashboard..." />
      </div>
    )
  }

  if (error) {
    return <Alert type="error" message="Failed to load dashboard data" showIcon />
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red'
      case 'high': return 'orange'
      case 'medium': return 'gold'
      case 'low': return 'blue'
      default: return 'default'
    }
  }

  const alertColumns = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Alert',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: 'Type',
      dataIndex: 'alert_type',
      key: 'alert_type',
    },
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ]

  const storagePercentage = stats
    ? Math.round((stats.storage.used_storage_mb / stats.storage.total_storage_mb) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>Analytics Dashboard</Title>
        <Space>
          <RangePicker />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Overview" key="overview">
          {/* Key Metrics */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Total Documents"
                  value={stats?.documents.total_documents || 0}
                  prefix={<FileOutlined />}
                  valueStyle={{ color: '#1E3A5F' }}
                />
                <div className="mt-2">
                  <Text type="secondary">
                    <ArrowUpOutlined style={{ color: '#52c41a' }} />
                    {' '}{stats?.documents.documents_today || 0} today
                  </Text>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Pending Approvals"
                  value={stats?.workflows.pending_approvals || 0}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: stats?.workflows.overdue_count ? '#ff4d4f' : '#faad14' }}
                />
                <div className="mt-2">
                  <Text type="danger">
                    {stats?.workflows.overdue_count || 0} overdue
                  </Text>
                </div>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Compliance Score"
                  value={stats?.compliance.compliance_score || 0}
                  suffix="%"
                  prefix={<SafetyOutlined />}
                  valueStyle={{
                    color: (stats?.compliance.compliance_score || 0) >= 80 ? '#52c41a' : '#faad14'
                  }}
                />
                <Progress
                  percent={stats?.compliance.compliance_score || 0}
                  showInfo={false}
                  strokeColor={(stats?.compliance.compliance_score || 0) >= 80 ? '#52c41a' : '#faad14'}
                />
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Storage Used"
                  value={stats?.storage.used_storage_mb || 0}
                  suffix={`/ ${stats?.storage.total_storage_mb || 0} MB`}
                  prefix={<CloudOutlined />}
                  valueStyle={{ color: storagePercentage > 80 ? '#ff4d4f' : '#1E3A5F' }}
                />
                <Progress
                  percent={storagePercentage}
                  showInfo={false}
                  strokeColor={storagePercentage > 80 ? '#ff4d4f' : '#1E3A5F'}
                />
              </Card>
            </Col>
          </Row>

          {/* Second Row - Additional Metrics */}
          <Row gutter={[16, 16]} className="mt-4">
            <Col xs={24} sm={12} lg={6}>
              <Card size="small">
                <Statistic
                  title="OCR Success Rate"
                  value={stats?.ocr.success_rate || 0}
                  suffix="%"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card size="small">
                <Statistic
                  title="Documents with PII"
                  value={stats?.compliance.documents_with_pii || 0}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card size="small">
                <Statistic
                  title="Active Legal Holds"
                  value={stats?.compliance.legal_holds_active || 0}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card size="small">
                <Statistic
                  title="WORM Records"
                  value={stats?.compliance.worm_records || 0}
                  valueStyle={{ color: '#1E3A5F' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Alerts Section */}
          <Row gutter={[16, 16]} className="mt-4">
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <WarningOutlined style={{ color: '#faad14' }} />
                    Active Alerts
                  </Space>
                }
              >
                <Table
                  dataSource={stats?.alerts || []}
                  columns={alertColumns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="Documents by Status">
                {stats?.documents.by_status && (
                  <div className="space-y-2">
                    {Object.entries(stats.documents.by_status).map(([status, count]) => (
                      <div key={status} className="flex justify-between items-center">
                        <Tag>{status.toUpperCase()}</Tag>
                        <span>{count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Documents" key="documents">
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="Documents by Type">
                {stats?.documents.by_type && (
                  <div className="space-y-2">
                    {Object.entries(stats.documents.by_type).map(([type, count]) => (
                      <div key={type} className="flex justify-between items-center">
                        <span>{type}</span>
                        <Tag color="blue">{count}</Tag>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="Documents by Department">
                {stats?.documents.by_department && (
                  <div className="space-y-2">
                    {Object.entries(stats.documents.by_department).map(([dept, count]) => (
                      <div key={dept} className="flex justify-between items-center">
                        <span>{dept}</span>
                        <Tag color="green">{count}</Tag>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Workflows" key="workflows">
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Approved Today"
                  value={stats?.workflows.approved_today || 0}
                  prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Rejected Today"
                  value={stats?.workflows.rejected_today || 0}
                  prefix={<ClockCircleOutlined style={{ color: '#ff4d4f' }} />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Avg. Approval Time"
                  value={stats?.workflows.avg_approval_time || 0}
                  suffix="hours"
                />
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Storage" key="storage">
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="Storage Usage">
                <div className="text-center mb-4">
                  <Progress
                    type="dashboard"
                    percent={storagePercentage}
                    strokeColor={storagePercentage > 80 ? '#ff4d4f' : '#1E3A5F'}
                  />
                </div>
                <Statistic
                  title="Total Used"
                  value={stats?.storage.used_storage_mb || 0}
                  suffix={`MB of ${stats?.storage.total_storage_mb || 0} MB`}
                />
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="Storage by Document Type">
                {stats?.storage.storage_by_type && (
                  <div className="space-y-2">
                    {Object.entries(stats.storage.storage_by_type).map(([type, size]) => (
                      <div key={type} className="flex justify-between items-center">
                        <span>{type}</span>
                        <Tag>{size} MB</Tag>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default AnalyticsDashboard

import React from 'react'
import { Row, Col, Card, Statistic, Typography, List, Tag, Progress, Spin } from 'antd'
import {
  FileOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ArrowUpOutlined,
  FileSearchOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { documentService } from '@/services/documentService'
import api from '@/services/api'

const { Title, Text } = Typography

interface DashboardSummary {
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
}

const DashboardPage: React.FC = () => {
  // Fetch dashboard analytics
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery<DashboardSummary>({
    queryKey: ['analytics', 'dashboard'],
    queryFn: () => api.get('/analytics/dashboard').then(r => r.data),
  })

  // Fetch recent documents
  const { data: documentsData } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => documentService.getDocuments({ page: 1, page_size: 5 }),
  })

  const recentDocuments = documentsData?.items || []

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      DRAFT: 'default',
      REVIEW: 'processing',
      APPROVED: 'success',
      ARCHIVED: 'warning',
    }
    return colors[status] || 'default'
  }

  if (dashboardLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Title level={3} className="mb-6">
        Dashboard
      </Title>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Documents"
              value={dashboardData?.documents?.total_documents || 0}
              prefix={<FileOutlined />}
              valueStyle={{ color: '#1E3A5F' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending Approval"
              value={dashboardData?.workflows?.pending_approvals || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#FFA000' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Approved Today"
              value={dashboardData?.workflows?.approved_today || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#388E3C' }}
              suffix={<ArrowUpOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="OCR Processing"
              value={dashboardData?.ocr?.pending || 0}
              prefix={<FileSearchOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Recent Documents */}
        <Col xs={24} lg={16}>
          <Card
            title="Recent Documents"
            extra={<a href="/documents">View All</a>}
          >
            <List
              dataSource={recentDocuments}
              renderItem={(doc) => (
                <List.Item
                  actions={[
                    <Tag key="status" color={getStatusColor(doc.lifecycle_status)}>
                      {doc.lifecycle_status}
                    </Tag>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileOutlined style={{ fontSize: 24, color: '#1E3A5F' }} />}
                    title={<a href={`/documents/${doc.id}`}>{doc.title}</a>}
                    description={
                      <span className="text-gray-500">
                        {doc.file_name} • {(doc.file_size / 1024).toFixed(1)} KB
                      </span>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No documents yet' }}
            />
          </Card>
        </Col>

        {/* Quick Stats */}
        <Col xs={24} lg={8}>
          <Card title="Document Distribution">
            <div className="space-y-4">
              {dashboardData?.documents?.by_status && Object.entries(dashboardData.documents.by_status).slice(0, 3).map(([status, count]) => {
                const total = dashboardData.documents.total_documents || 1
                const percent = Math.round((count / total) * 100)
                const colors: Record<string, string> = {
                  DRAFT: '#1E3A5F',
                  REVIEW: '#FFA000',
                  APPROVED: '#2E7D32',
                  ARCHIVED: '#B8860B',
                }
                return (
                  <div key={status}>
                    <div className="flex justify-between mb-1">
                      <Text>{status}</Text>
                      <Text strong>{percent}%</Text>
                    </div>
                    <Progress percent={percent} strokeColor={colors[status] || '#1890ff'} showInfo={false} />
                  </div>
                )
              })}
            </div>
          </Card>

          <Card title="Compliance Status" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircleOutlined className="text-green-500" />
                  <Text>Compliance Score</Text>
                </div>
                <Text strong className="text-green-500">{dashboardData?.compliance?.compliance_score?.toFixed(0) || 0}%</Text>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ExclamationCircleOutlined className="text-yellow-500" />
                  <Text>Expiring Soon</Text>
                </div>
                <Text strong className="text-yellow-500">{dashboardData?.compliance?.retention_expiring_soon || 0}</Text>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ClockCircleOutlined className="text-blue-500" />
                  <Text>Legal Holds</Text>
                </div>
                <Text strong className="text-blue-500">{dashboardData?.compliance?.legal_holds_active || 0}</Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage

import React from 'react'
import { Row, Col, Card, Statistic, Typography, List, Tag, Progress } from 'antd'
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

const { Title, Text } = Typography

const DashboardPage: React.FC = () => {
  // Fetch recent documents
  const { data: documentsData } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => documentService.getDocuments({ page: 1, page_size: 5 }),
  })

  // Stats data (would come from analytics API in production)
  const stats = {
    total_documents: documentsData?.total || 0,
    pending_approval: 12,
    approved_today: 8,
    processing: 3,
  }

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
              value={stats.total_documents}
              prefix={<FileOutlined />}
              valueStyle={{ color: '#1E3A5F' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending Approval"
              value={stats.pending_approval}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#FFA000' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Approved Today"
              value={stats.approved_today}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#388E3C' }}
              suffix={<ArrowUpOutlined style={{ fontSize: 14 }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Processing"
              value={stats.processing}
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
              <div>
                <div className="flex justify-between mb-1">
                  <Text>Customer Documents</Text>
                  <Text strong>45%</Text>
                </div>
                <Progress percent={45} strokeColor="#1E3A5F" showInfo={false} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <Text>Vendor Documents</Text>
                  <Text strong>35%</Text>
                </div>
                <Progress percent={35} strokeColor="#2E7D32" showInfo={false} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <Text>Internal Documents</Text>
                  <Text strong>20%</Text>
                </div>
                <Progress percent={20} strokeColor="#B8860B" showInfo={false} />
              </div>
            </div>
          </Card>

          <Card title="Compliance Status" className="mt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircleOutlined className="text-green-500" />
                  <Text>Retention Compliant</Text>
                </div>
                <Text strong className="text-green-500">98%</Text>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ExclamationCircleOutlined className="text-yellow-500" />
                  <Text>Expiring Soon</Text>
                </div>
                <Text strong className="text-yellow-500">5</Text>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ClockCircleOutlined className="text-blue-500" />
                  <Text>Legal Hold</Text>
                </div>
                <Text strong className="text-blue-500">3</Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage

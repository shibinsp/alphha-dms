import React, { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  DatePicker,
  message,
  Descriptions,
  Statistic,
  Row,
  Col,
  Dropdown,
} from 'antd'
import {
  PlusOutlined,
  SafetyOutlined,
  ExportOutlined,
  UnlockOutlined,
  EyeOutlined,
  MoreOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import api from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input

interface LegalHold {
  id: string
  hold_name: string
  case_number: string | null
  matter_name: string | null
  description: string | null
  legal_counsel: string | null
  status: 'ACTIVE' | 'RELEASED' | 'EXPIRED'
  documents_held: number
  total_size_bytes: number
  hold_start_date: string
  hold_end_date: string | null
  created_at: string
  released_at: string | null
  release_reason: string | null
}

const LegalHoldsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [releaseModalOpen, setReleaseModalOpen] = useState(false)
  const [selectedHold, setSelectedHold] = useState<LegalHold | null>(null)
  const [form] = Form.useForm()
  const [releaseReason, setReleaseReason] = useState('')

  const { data: legalHolds, isLoading } = useQuery({
    queryKey: ['legal-holds'],
    queryFn: async () => {
      const response = await api.get('/compliance/legal-holds')
      return response.data as LegalHold[]
    },
  })

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      await api.post('/compliance/legal-holds', data)
    },
    onSuccess: () => {
      message.success('Legal hold created successfully')
      queryClient.invalidateQueries({ queryKey: ['legal-holds'] })
      setCreateModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Failed to create legal hold')
    },
  })

  const releaseMutation = useMutation({
    mutationFn: async ({ holdId, reason }: { holdId: string; reason: string }) => {
      await api.post(`/compliance/legal-holds/${holdId}/release`, { reason })
    },
    onSuccess: () => {
      message.success('Legal hold released')
      queryClient.invalidateQueries({ queryKey: ['legal-holds'] })
      setReleaseModalOpen(false)
      setSelectedHold(null)
      setReleaseReason('')
    },
    onError: () => {
      message.error('Failed to release legal hold')
    },
  })

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      ACTIVE: 'green',
      RELEASED: 'default',
      EXPIRED: 'orange',
    }
    return colors[status] || 'default'
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const columns: ColumnsType<LegalHold> = [
    {
      title: 'Hold Name',
      dataIndex: 'hold_name',
      key: 'hold_name',
      render: (name: string, record) => (
        <Space>
          <SafetyOutlined className="text-orange-500" />
          <a onClick={() => {
            setSelectedHold(record)
            setDetailModalOpen(true)
          }}>{name}</a>
        </Space>
      ),
    },
    {
      title: 'Case Number',
      dataIndex: 'case_number',
      key: 'case_number',
      render: (num) => num || '-',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: 'Documents',
      dataIndex: 'documents_held',
      key: 'documents_held',
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'Size',
      dataIndex: 'total_size_bytes',
      key: 'total_size_bytes',
      render: (bytes: number) => formatBytes(bytes),
    },
    {
      title: 'Start Date',
      dataIndex: 'hold_start_date',
      key: 'hold_start_date',
      render: (date: string) => dayjs(date).format('MMM D, YYYY'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: 'View Details',
                onClick: () => {
                  setSelectedHold(record)
                  setDetailModalOpen(true)
                },
              },
              {
                key: 'export',
                icon: <ExportOutlined />,
                label: 'Export Evidence',
                disabled: record.status !== 'ACTIVE',
              },
              { type: 'divider' },
              {
                key: 'release',
                icon: <UnlockOutlined />,
                label: 'Release Hold',
                danger: true,
                disabled: record.status !== 'ACTIVE',
                onClick: () => {
                  setSelectedHold(record)
                  setReleaseModalOpen(true)
                },
              },
            ],
          }}
          trigger={['click']}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ]

  const activeHolds = legalHolds?.filter((h) => h.status === 'ACTIVE') || []
  const totalDocuments = legalHolds?.reduce((sum, h) => sum + h.documents_held, 0) || 0

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={3} className="mb-0">
          Legal Holds
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          Create Legal Hold
        </Button>
      </div>

      {/* Stats */}
      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Holds"
              value={activeHolds.length}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#2E7D32' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Documents Under Hold"
              value={totalDocuments}
              valueStyle={{ color: '#1E3A5F' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Released Holds"
              value={legalHolds?.filter((h) => h.status === 'RELEASED').length || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Holds"
              value={legalHolds?.length || 0}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={legalHolds}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `${total} legal holds`,
          }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Create Legal Hold"
        open={createModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          setCreateModalOpen(false)
          form.resetFields()
        }}
        okText="Create"
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => {
            createMutation.mutate({
              ...values,
              hold_end_date: values.hold_end_date?.toISOString(),
            })
          }}
        >
          <Form.Item
            name="hold_name"
            label="Hold Name"
            rules={[{ required: true, message: 'Please enter hold name' }]}
          >
            <Input placeholder="Enter hold name" />
          </Form.Item>

          <Form.Item name="case_number" label="Case Number">
            <Input placeholder="Enter case number" />
          </Form.Item>

          <Form.Item name="matter_name" label="Matter Name">
            <Input placeholder="Enter matter name" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Enter description" />
          </Form.Item>

          <Form.Item name="legal_counsel" label="Legal Counsel">
            <Input placeholder="Enter legal counsel name" />
          </Form.Item>

          <Form.Item name="counsel_email" label="Counsel Email">
            <Input type="email" placeholder="Enter counsel email" />
          </Form.Item>

          <Form.Item name="hold_end_date" label="End Date (optional)">
            <DatePicker className="w-full" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="Legal Hold Details"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false)
          setSelectedHold(null)
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Close
          </Button>,
          selectedHold?.status === 'ACTIVE' && (
            <Button
              key="release"
              danger
              onClick={() => {
                setDetailModalOpen(false)
                setReleaseModalOpen(true)
              }}
            >
              Release Hold
            </Button>
          ),
        ]}
        width={700}
      >
        {selectedHold && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Hold Name" span={2}>
              {selectedHold.hold_name}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={getStatusColor(selectedHold.status)}>
                {selectedHold.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Case Number">
              {selectedHold.case_number || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Matter Name">
              {selectedHold.matter_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Legal Counsel">
              {selectedHold.legal_counsel || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Documents Held">
              {selectedHold.documents_held.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Total Size">
              {formatBytes(selectedHold.total_size_bytes)}
            </Descriptions.Item>
            <Descriptions.Item label="Start Date">
              {dayjs(selectedHold.hold_start_date).format('MMM D, YYYY h:mm A')}
            </Descriptions.Item>
            <Descriptions.Item label="End Date">
              {selectedHold.hold_end_date
                ? dayjs(selectedHold.hold_end_date).format('MMM D, YYYY')
                : 'No end date'}
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {selectedHold.description || '-'}
            </Descriptions.Item>
            {selectedHold.released_at && (
              <>
                <Descriptions.Item label="Released At">
                  {dayjs(selectedHold.released_at).format('MMM D, YYYY h:mm A')}
                </Descriptions.Item>
                <Descriptions.Item label="Release Reason">
                  {selectedHold.release_reason}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* Release Modal */}
      <Modal
        title="Release Legal Hold"
        open={releaseModalOpen}
        onOk={() => {
          if (!selectedHold) return
          if (!releaseReason.trim()) {
            message.error('Please provide a reason for releasing the hold')
            return
          }
          releaseMutation.mutate({
            holdId: selectedHold.id,
            reason: releaseReason,
          })
        }}
        onCancel={() => {
          setReleaseModalOpen(false)
          setSelectedHold(null)
          setReleaseReason('')
        }}
        okText="Release Hold"
        okButtonProps={{ danger: true, loading: releaseMutation.isPending }}
      >
        <div className="py-4">
          <Text type="warning" className="block mb-4">
            Warning: Releasing this legal hold will remove the hold status from {selectedHold?.documents_held} documents.
          </Text>
          <Text className="block mb-2">Reason for releasing (required):</Text>
          <TextArea
            rows={4}
            value={releaseReason}
            onChange={(e) => setReleaseReason(e.target.value)}
            placeholder="Enter the reason for releasing this legal hold..."
          />
        </div>
      </Modal>
    </div>
  )
}

export default LegalHoldsPage

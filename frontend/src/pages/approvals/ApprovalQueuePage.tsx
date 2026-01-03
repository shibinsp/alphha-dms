import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Modal,
  Input,
  message,
  Badge,
  Tooltip,
} from 'antd'
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import api from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input

interface ApprovalRequest {
  id: string
  workflow_id: string
  document_id: string
  status: string
  current_step: number
  priority: string
  deadline: string | null
  requested_by: string
  requested_at: string
  document?: {
    id: string
    title: string
    file_name: string
  }
  workflow?: {
    id: string
    name: string
    workflow_type: string
  }
}

const ApprovalQueuePage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedRequest, setSelectedRequest] = React.useState<ApprovalRequest | null>(null)
  const [actionModal, setActionModal] = React.useState<'approve' | 'reject' | null>(null)
  const [comments, setComments] = React.useState('')

  const { data: pendingApprovals, isLoading } = useQuery({
    queryKey: ['pending-approvals'],
    queryFn: async () => {
      const response = await api.get('/workflows/requests/pending')
      return response.data as ApprovalRequest[]
    },
  })

  const approveMutation = useMutation({
    mutationFn: async ({ requestId, comments }: { requestId: string; comments?: string }) => {
      await api.post(`/workflows/requests/${requestId}/approve`, { comments })
    },
    onSuccess: () => {
      message.success('Document approved successfully')
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      setActionModal(null)
      setSelectedRequest(null)
      setComments('')
    },
    onError: () => {
      message.error('Failed to approve document')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, comments }: { requestId: string; comments?: string }) => {
      await api.post(`/workflows/requests/${requestId}/reject`, { comments })
    },
    onSuccess: () => {
      message.success('Document rejected')
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      setActionModal(null)
      setSelectedRequest(null)
      setComments('')
    },
    onError: () => {
      message.error('Failed to reject document')
    },
  })

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      LOW: 'default',
      NORMAL: 'blue',
      HIGH: 'orange',
      URGENT: 'red',
    }
    return colors[priority] || 'default'
  }

  const isOverdue = (deadline: string | null) => {
    if (!deadline) return false
    return dayjs(deadline).isBefore(dayjs())
  }

  const columns: ColumnsType<ApprovalRequest> = [
    {
      title: 'Document',
      key: 'document',
      render: (_, record) => (
        <div>
          <Text strong>{record.document?.title || 'Unknown'}</Text>
          <br />
          <Text type="secondary" className="text-xs">
            {record.document?.file_name}
          </Text>
        </div>
      ),
    },
    {
      title: 'Workflow',
      dataIndex: ['workflow', 'name'],
      key: 'workflow',
      render: (name: string, record) => (
        <div>
          <Text>{name}</Text>
          <br />
          <Tag>{record.workflow?.workflow_type}</Tag>
        </div>
      ),
    },
    {
      title: 'Step',
      dataIndex: 'current_step',
      key: 'current_step',
      render: (step: number) => <Tag color="blue">Step {step}</Tag>,
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>{priority}</Tag>
      ),
    },
    {
      title: 'Deadline',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (deadline: string | null) => {
        if (!deadline) return '-'
        const overdue = isOverdue(deadline)
        return (
          <Space>
            {overdue && <ExclamationCircleOutlined className="text-red-500" />}
            <Text type={overdue ? 'danger' : undefined}>
              {dayjs(deadline).format('MMM D, YYYY')}
            </Text>
          </Space>
        )
      },
    },
    {
      title: 'Requested',
      dataIndex: 'requested_at',
      key: 'requested_at',
      render: (date: string) => dayjs(date).format('MMM D, YYYY h:mm A'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title="View Document">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/documents/${record.document_id}`)}
            />
          </Tooltip>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={() => {
              setSelectedRequest(record)
              setActionModal('approve')
            }}
          >
            Approve
          </Button>
          <Button
            danger
            icon={<CloseOutlined />}
            onClick={() => {
              setSelectedRequest(record)
              setActionModal('reject')
            }}
          >
            Reject
          </Button>
        </Space>
      ),
    },
  ]

  const handleAction = () => {
    if (!selectedRequest) return

    if (actionModal === 'approve') {
      approveMutation.mutate({
        requestId: selectedRequest.id,
        comments: comments || undefined,
      })
    } else if (actionModal === 'reject') {
      rejectMutation.mutate({
        requestId: selectedRequest.id,
        comments: comments || undefined,
      })
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <Title level={3} className="mb-0">
            Approval Queue
          </Title>
          <Badge
            count={pendingApprovals?.length || 0}
            style={{ backgroundColor: '#1E3A5F' }}
          />
        </div>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={pendingApprovals}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `${total} pending approvals`,
          }}
          locale={{ emptyText: 'No pending approvals' }}
        />
      </Card>

      {/* Approve/Reject Modal */}
      <Modal
        title={actionModal === 'approve' ? 'Approve Document' : 'Reject Document'}
        open={!!actionModal}
        onOk={handleAction}
        onCancel={() => {
          setActionModal(null)
          setSelectedRequest(null)
          setComments('')
        }}
        okText={actionModal === 'approve' ? 'Approve' : 'Reject'}
        okButtonProps={{
          danger: actionModal === 'reject',
          loading: approveMutation.isPending || rejectMutation.isPending,
        }}
      >
        <div className="py-4">
          <Text>
            {actionModal === 'approve'
              ? 'Are you sure you want to approve this document?'
              : 'Are you sure you want to reject this document?'}
          </Text>
          <div className="mt-4">
            <Text type="secondary">Comments (optional)</Text>
            <TextArea
              rows={4}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Enter any comments..."
              className="mt-2"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default ApprovalQueuePage

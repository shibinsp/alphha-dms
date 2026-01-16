import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Modal, Select, Input, message, Space, Tabs, Badge } from 'antd'
import { CheckOutlined, CloseOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { accessRequestService, AccessRequest, PermissionLevel } from '@/services/accessRequestService'
import dayjs from 'dayjs'

const { TextArea } = Input

const permissionOptions = [
  { value: 'VIEWER_NO_DOWNLOAD', label: 'View Only' },
  { value: 'VIEWER_DOWNLOAD', label: 'View & Download' },
  { value: 'EDITOR', label: 'Edit' },
  { value: 'COMMENTER', label: 'Comment' },
]

const statusColors: Record<string, string> = {
  PENDING: 'orange',
  APPROVED: 'green',
  REJECTED: 'red',
  REASON_REQUESTED: 'blue',
}

export default function AccessRequestsPage() {
  const [myRequests, setMyRequests] = useState<AccessRequest[]>([])
  const [pendingRequests, setPendingRequests] = useState<AccessRequest[]>([])
  const [processedRequests, setProcessedRequests] = useState<AccessRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [responseModal, setResponseModal] = useState<{ visible: boolean; request?: AccessRequest; action?: 'approve' | 'reject' | 'ask' }>({ visible: false })
  const [grantedPermission, setGrantedPermission] = useState<PermissionLevel>()
  const [comment, setComment] = useState('')
  const [reasonModal, setReasonModal] = useState<{ visible: boolean; request?: AccessRequest }>({ visible: false })
  const [reason, setReason] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const [my, pending, processed] = await Promise.all([
        accessRequestService.getMyRequests(),
        accessRequestService.getPendingRequests(),
        accessRequestService.getProcessedRequests()
      ])
      setMyRequests(my)
      setPendingRequests(pending)
      setProcessedRequests(processed)
    } catch {
      message.error('Failed to load requests')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const handleResponse = async () => {
    if (!responseModal.request) return
    try {
      if (responseModal.action === 'approve') {
        await accessRequestService.approveRequest(responseModal.request.id, grantedPermission, comment)
        message.success('Request approved')
      } else if (responseModal.action === 'reject') {
        await accessRequestService.rejectRequest(responseModal.request.id, comment)
        message.success('Request rejected')
      } else if (responseModal.action === 'ask') {
        await accessRequestService.askForReason(responseModal.request.id, comment)
        message.success('Reason requested')
      }
      setResponseModal({ visible: false })
      setComment('')
      setGrantedPermission(undefined)
      fetchData()
    } catch {
      message.error('Action failed')
    }
  }

  const handleUpdateReason = async () => {
    if (!reasonModal.request) return
    try {
      await accessRequestService.updateRequest(reasonModal.request.id, reason)
      message.success('Reason submitted')
      setReasonModal({ visible: false })
      setReason('')
      fetchData()
    } catch {
      message.error('Failed to submit reason')
    }
  }

  const handleCancel = async (id: string) => {
    try {
      await accessRequestService.cancelRequest(id)
      message.success('Request cancelled')
      fetchData()
    } catch {
      message.error('Failed to cancel')
    }
  }

  const myRequestsColumns = [
    { title: 'Document', dataIndex: ['document', 'title'], key: 'document', render: (t: string) => t || 'N/A' },
    { title: 'Requested', dataIndex: 'requested_permission', key: 'requested' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag> },
    { title: 'Granted', dataIndex: 'granted_permission', key: 'granted', render: (p: string) => p || '-' },
    { title: 'Owner Comment', dataIndex: 'owner_comment', key: 'comment', render: (c: string) => c || '-' },
    { title: 'Date', dataIndex: 'created_at', key: 'date', render: (d: string) => dayjs(d).format('MMM D, YYYY') },
    {
      title: 'Action', key: 'action',
      render: (_: unknown, r: AccessRequest) => (
        <Space>
          {r.status === 'REASON_REQUESTED' && (
            <Button size="small" onClick={() => { setReasonModal({ visible: true, request: r }); setReason(r.reason || '') }}>
              Add Reason
            </Button>
          )}
          {['PENDING', 'REASON_REQUESTED'].includes(r.status) && (
            <Button size="small" danger onClick={() => handleCancel(r.id)}>Cancel</Button>
          )}
        </Space>
      )
    }
  ]

  const pendingColumns = [
    { title: 'Document', dataIndex: ['document', 'title'], key: 'document', render: (t: string) => t || 'N/A' },
    { title: 'Requester', dataIndex: ['requester', 'full_name'], key: 'requester' },
    { title: 'Email', dataIndex: ['requester', 'email'], key: 'email' },
    { title: 'Requested', dataIndex: 'requested_permission', key: 'requested' },
    { title: 'Reason', dataIndex: 'reason', key: 'reason', render: (r: string) => r || <Tag color="orange">Not provided</Tag> },
    { title: 'Date', dataIndex: 'created_at', key: 'date', render: (d: string) => dayjs(d).format('MMM D, YYYY') },
    {
      title: 'Action', key: 'action',
      render: (_: unknown, r: AccessRequest) => (
        <Space>
          <Button type="primary" size="small" icon={<CheckOutlined />}
            onClick={() => setResponseModal({ visible: true, request: r, action: 'approve' })}>
            Approve
          </Button>
          <Button danger size="small" icon={<CloseOutlined />}
            onClick={() => setResponseModal({ visible: true, request: r, action: 'reject' })}>
            Reject
          </Button>
          {!r.reason && (
            <Button size="small" icon={<QuestionCircleOutlined />}
              onClick={() => setResponseModal({ visible: true, request: r, action: 'ask' })}>
              Ask Reason
            </Button>
          )}
        </Space>
      )
    }
  ]

  const processedColumns = [
    { title: 'Document', dataIndex: ['document', 'title'], key: 'document', render: (t: string) => t || 'N/A' },
    { title: 'Requester', dataIndex: ['requester', 'full_name'], key: 'requester' },
    { title: 'Email', dataIndex: ['requester', 'email'], key: 'email' },
    { title: 'Requested', dataIndex: 'requested_permission', key: 'requested' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag> },
    { title: 'Granted', dataIndex: 'granted_permission', key: 'granted', render: (p: string) => p || '-' },
    { title: 'Comment', dataIndex: 'owner_comment', key: 'comment', render: (c: string) => c || '-' },
    { title: 'Responded', dataIndex: 'responded_at', key: 'responded', render: (d: string) => d ? dayjs(d).format('MMM D, YYYY') : '-' },
  ]

  return (
    <div className="p-6">
      <Card title="Access Requests">
        <Tabs items={[
          {
            key: 'pending',
            label: <Badge count={pendingRequests.length} offset={[10, 0]}>Pending Approvals</Badge>,
            children: <Table dataSource={pendingRequests} columns={pendingColumns} rowKey="id" loading={loading} />
          },
          {
            key: 'processed',
            label: 'Processed',
            children: <Table dataSource={processedRequests} columns={processedColumns} rowKey="id" loading={loading} />
          },
          {
            key: 'my',
            label: 'My Requests',
            children: <Table dataSource={myRequests} columns={myRequestsColumns} rowKey="id" loading={loading} />
          }
        ]} />
      </Card>

      <Modal
        title={responseModal.action === 'approve' ? 'Approve Request' : responseModal.action === 'reject' ? 'Reject Request' : 'Ask for Reason'}
        open={responseModal.visible}
        onOk={handleResponse}
        onCancel={() => { setResponseModal({ visible: false }); setComment(''); setGrantedPermission(undefined) }}
      >
        {responseModal.action === 'approve' && (
          <div className="mb-4">
            <label className="block mb-2">Grant Permission Level:</label>
            <Select
              className="w-full"
              placeholder="Same as requested"
              options={permissionOptions}
              value={grantedPermission}
              onChange={setGrantedPermission}
              allowClear
            />
          </div>
        )}
        <div>
          <label className="block mb-2">{responseModal.action === 'ask' ? 'Message to requester:' : 'Comment (optional):'}</label>
          <TextArea rows={3} value={comment} onChange={e => setComment(e.target.value)} />
        </div>
      </Modal>

      <Modal
        title="Provide Reason"
        open={reasonModal.visible}
        onOk={handleUpdateReason}
        onCancel={() => { setReasonModal({ visible: false }); setReason('') }}
      >
        <p className="mb-2">Owner requested: {reasonModal.request?.owner_comment}</p>
        <TextArea rows={3} value={reason} onChange={e => setReason(e.target.value)} placeholder="Enter your reason for access..." />
      </Modal>
    </div>
  )
}

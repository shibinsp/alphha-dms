import React, { useState } from 'react'
import {
  Table,
  Button,
  Space,
  Select,
  InputNumber,
  Popconfirm,
  message,
  Typography,
  Tag,
  Modal,
  Form,
  Input,
  Empty,
  Tooltip,
  Switch,
} from 'antd'
import {
  LinkOutlined,
  CopyOutlined,
  DeleteOutlined,
  PlusOutlined,
  EyeOutlined,
  DownloadOutlined,
  EditOutlined,
  LockOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sharingService, type ShareLink, type CreateShareLinkRequest } from '@/services/sharingService'
import dayjs from 'dayjs'

const { Text } = Typography

interface ShareLinksProps {
  documentId: string
  canManage: boolean
}

const getLinkTypeIcon = (type: string) => {
  switch (type) {
    case 'VIEW':
      return <EyeOutlined />
    case 'DOWNLOAD':
      return <DownloadOutlined />
    case 'EDIT':
      return <EditOutlined />
    default:
      return <LinkOutlined />
  }
}

const getLinkTypeColor = (type: string) => {
  switch (type) {
    case 'VIEW':
      return 'blue'
    case 'DOWNLOAD':
      return 'green'
    case 'EDIT':
      return 'orange'
    default:
      return 'default'
  }
}

const ShareLinks: React.FC<ShareLinksProps> = ({ documentId, canManage }) => {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [usePassword, setUsePassword] = useState(false)
  const [form] = Form.useForm()

  // Fetch share links
  const { data: shareLinks = [], isLoading } = useQuery({
    queryKey: ['document-share-links', documentId],
    queryFn: () => sharingService.getShareLinks(documentId),
  })

  // Create share link mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateShareLinkRequest) => sharingService.createShareLink(documentId, data),
    onSuccess: (data) => {
      message.success('Share link created')
      queryClient.invalidateQueries({ queryKey: ['document-share-links', documentId] })
      setIsModalOpen(false)
      form.resetFields()
      setUsePassword(false)

      // Copy to clipboard
      const fullUrl = `${window.location.origin}${data.url}`
      navigator.clipboard.writeText(fullUrl)
      message.info('Link copied to clipboard!')
    },
    onError: () => {
      message.error('Failed to create share link')
    },
  })

  // Deactivate share link mutation
  const deactivateMutation = useMutation({
    mutationFn: (linkId: string) => sharingService.deactivateShareLink(documentId, linkId),
    onSuccess: () => {
      message.success('Share link deactivated')
      queryClient.invalidateQueries({ queryKey: ['document-share-links', documentId] })
    },
    onError: () => {
      message.error('Failed to deactivate share link')
    },
  })

  const handleCopyLink = (link: ShareLink) => {
    const fullUrl = `${window.location.origin}${link.url}`
    navigator.clipboard.writeText(fullUrl)
    message.success('Link copied to clipboard!')
  }

  const handleSubmit = (values: any) => {
    const data: CreateShareLinkRequest = {
      link_type: values.link_type,
      expires_in_days: values.expires_in_days,
      max_downloads: values.max_downloads,
    }

    if (usePassword && values.password) {
      data.password = values.password
    }

    createMutation.mutate(data)
  }

  const columns = [
    {
      title: 'Link',
      key: 'link',
      render: (record: ShareLink) => (
        <Space>
          <LinkOutlined />
          <Text copyable={{ text: `${window.location.origin}${record.url}` }}>
            {record.token.slice(0, 12)}...
          </Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'link_type',
      key: 'link_type',
      render: (type: string) => (
        <Tag icon={getLinkTypeIcon(type)} color={getLinkTypeColor(type)}>
          {type}
        </Tag>
      ),
    },
    {
      title: 'Downloads',
      key: 'downloads',
      render: (record: ShareLink) => (
        <Text>
          {record.download_count}
          {record.max_downloads && ` / ${record.max_downloads}`}
        </Text>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (record: ShareLink) => {
        if (!record.is_active) {
          return <Tag color="red">Inactive</Tag>
        }
        if (record.expires_at && dayjs(record.expires_at).isBefore(dayjs())) {
          return <Tag color="orange">Expired</Tag>
        }
        if (record.max_downloads && record.download_count >= record.max_downloads) {
          return <Tag color="orange">Limit Reached</Tag>
        }
        return <Tag color="green">Active</Tag>
      },
    },
    {
      title: 'Expires',
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (date: string | null) => {
        if (!date) return <Text type="secondary">Never</Text>
        const expiry = dayjs(date)
        const isExpired = expiry.isBefore(dayjs())
        return (
          <Tooltip title={expiry.format('YYYY-MM-DD HH:mm')}>
            <Text type={isExpired ? 'danger' : undefined}>
              {isExpired ? 'Expired' : expiry.fromNow()}
            </Text>
          </Tooltip>
        )
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: ShareLink) => (
        <Space>
          <Tooltip title="Copy Link">
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => handleCopyLink(record)}
            />
          </Tooltip>
          {canManage && record.is_active && (
            <Popconfirm
              title="Deactivate link?"
              description="This link will no longer work."
              onConfirm={() => deactivateMutation.mutate(record.id)}
              okText="Deactivate"
              cancelText="Cancel"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                loading={deactivateMutation.isPending}
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-4">
        <Text strong>Share Links ({shareLinks.length})</Text>
        {canManage && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsModalOpen(true)}
          >
            Create Link
          </Button>
        )}
      </div>

      {shareLinks.length === 0 ? (
        <Empty
          description="No share links"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Table
          dataSource={shareLinks}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
      )}

      {/* Create Share Link Modal */}
      <Modal
        title="Create Share Link"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          form.resetFields()
          setUsePassword(false)
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            link_type: 'VIEW',
            expires_in_days: 7,
          }}
        >
          <Form.Item
            name="link_type"
            label="Link Type"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="VIEW">
                <Space>
                  <EyeOutlined />
                  <span>View Only</span>
                </Space>
              </Select.Option>
              <Select.Option value="DOWNLOAD">
                <Space>
                  <DownloadOutlined />
                  <span>View & Download</span>
                </Space>
              </Select.Option>
              <Select.Option value="EDIT">
                <Space>
                  <EditOutlined />
                  <span>View & Edit</span>
                </Space>
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="expires_in_days" label="Expires In (Days)">
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="max_downloads" label="Max Downloads (Optional)">
            <InputNumber min={1} max={1000} style={{ width: '100%' }} placeholder="Unlimited" />
          </Form.Item>

          <Form.Item label="Password Protection">
            <Switch
              checked={usePassword}
              onChange={setUsePassword}
              checkedChildren={<LockOutlined />}
            />
          </Form.Item>

          {usePassword && (
            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true, message: 'Enter password' }]}
            >
              <Input.Password placeholder="Enter password for link" />
            </Form.Item>
          )}

          <Form.Item className="mb-0">
            <Space className="w-full justify-end">
              <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                Create Link
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ShareLinks

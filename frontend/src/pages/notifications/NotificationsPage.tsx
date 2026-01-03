import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card,
  List,
  Typography,
  Button,
  Spin,
  Space,
  Tag,
  Empty,
  Badge,
  Tabs,
  Switch,
  message,
  Avatar,
} from 'antd'
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
  FileOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ShareAltOutlined,
  SafetyOutlined,
  CommentOutlined,
  TeamOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'

const { Title, Text, Paragraph } = Typography

interface Notification {
  id: string
  notification_type: string
  priority: string
  title: string
  message: string
  entity_type?: string
  entity_id?: string
  action_url?: string
  is_read: boolean
  read_at?: string
  created_at: string
}

interface NotificationPreference {
  id: string
  notification_type: string
  in_app_enabled: boolean
  email_enabled: boolean
  push_enabled: boolean
  email_digest: string
}

const NotificationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications', activeTab === 'unread'],
    queryFn: async () => {
      const response = await api.get('/notifications', {
        params: { unread_only: activeTab === 'unread' },
      })
      return response.data
    },
  })

  const { data: preferences, isLoading: loadingPrefs } = useQuery<NotificationPreference[]>({
    queryKey: ['notifications', 'preferences'],
    queryFn: async () => {
      const response = await api.get('/notifications/preferences')
      return response.data
    },
  })

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) =>
      api.put(`/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => api.put('/notifications/read-all'),
    onSuccess: () => {
      message.success('All notifications marked as read')
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (notificationId: string) =>
      api.delete(`/notifications/${notificationId}`),
    onSuccess: () => {
      message.success('Notification deleted')
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const updatePrefMutation = useMutation({
    mutationFn: ({
      type,
      field,
      value,
    }: {
      type: string
      field: string
      value: boolean
    }) => api.put(`/notifications/preferences/${type}`, { [field]: value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'preferences'] })
    },
  })

  const getNotificationIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      document_shared: <ShareAltOutlined style={{ color: '#1890ff' }} />,
      document_approved: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      document_rejected: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
      approval_requested: <FileOutlined style={{ color: '#faad14' }} />,
      pii_detected: <SafetyOutlined style={{ color: '#ff4d4f' }} />,
      legal_hold_applied: <SafetyOutlined style={{ color: '#ff4d4f' }} />,
      mention: <TeamOutlined style={{ color: '#1890ff' }} />,
      document_commented: <CommentOutlined style={{ color: '#1890ff' }} />,
    }
    return icons[type] || <BellOutlined />
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'red'
      case 'high':
        return 'orange'
      case 'normal':
        return 'blue'
      case 'low':
        return 'default'
      default:
        return 'default'
    }
  }

  const formatNotificationType = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id)
    }
    if (notification.action_url) {
      navigate(notification.action_url)
    }
  }

  const notifications = notificationsData?.items || []
  const unreadCount = notificationsData?.unread_count || 0

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>
          <Badge count={unreadCount} offset={[10, 0]}>
            <BellOutlined className="mr-2" />
          </Badge>
          Notifications
        </Title>
        <Space>
          <Button
            onClick={() => markAllReadMutation.mutate()}
            disabled={unreadCount === 0}
            loading={markAllReadMutation.isPending}
          >
            <CheckOutlined /> Mark All Read
          </Button>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane
          tab={
            <span>
              All <Badge count={notifications.length} showZero />
            </span>
          }
          key="all"
        >
          {isLoading ? (
            <Spin />
          ) : notifications.length ? (
            <List
              itemLayout="horizontal"
              dataSource={notifications}
              renderItem={(item: Notification) => (
                <List.Item
                  className={`cursor-pointer hover:bg-gray-50 ${
                    !item.is_read ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => handleNotificationClick(item)}
                  actions={[
                    !item.is_read && (
                      <Button
                        type="text"
                        size="small"
                        icon={<CheckOutlined />}
                        onClick={(e) => {
                          e.stopPropagation()
                          markReadMutation.mutate(item.id)
                        }}
                      >
                        Mark Read
                      </Button>
                    ),
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteMutation.mutate(item.id)
                      }}
                    />,
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={getNotificationIcon(item.notification_type)}
                        style={{
                          backgroundColor: item.is_read ? '#f0f0f0' : '#e6f7ff',
                        }}
                      />
                    }
                    title={
                      <Space>
                        <Text strong={!item.is_read}>{item.title}</Text>
                        <Tag color={getPriorityColor(item.priority)}>
                          {item.priority}
                        </Tag>
                      </Space>
                    }
                    description={
                      <div>
                        <Paragraph
                          ellipsis={{ rows: 2 }}
                          className="mb-1"
                          type={item.is_read ? 'secondary' : undefined}
                        >
                          {item.message}
                        </Paragraph>
                        <Text type="secondary" className="text-xs">
                          {new Date(item.created_at).toLocaleString()}
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="No notifications" />
          )}
        </Tabs.TabPane>

        <Tabs.TabPane
          tab={
            <span>
              Unread <Badge count={unreadCount} showZero />
            </span>
          }
          key="unread"
        />

        <Tabs.TabPane
          tab={
            <span>
              <SettingOutlined /> Preferences
            </span>
          }
          key="preferences"
        >
          {loadingPrefs ? (
            <Spin />
          ) : (
            <Card>
              <List
                itemLayout="horizontal"
                dataSource={preferences || []}
                renderItem={(pref: NotificationPreference) => (
                  <List.Item>
                    <List.Item.Meta
                      title={formatNotificationType(pref.notification_type)}
                    />
                    <Space size="large">
                      <div className="text-center">
                        <div className="mb-1">
                          <Text type="secondary">In-App</Text>
                        </div>
                        <Switch
                          checked={pref.in_app_enabled}
                          onChange={(checked) =>
                            updatePrefMutation.mutate({
                              type: pref.notification_type,
                              field: 'in_app_enabled',
                              value: checked,
                            })
                          }
                        />
                      </div>
                      <div className="text-center">
                        <div className="mb-1">
                          <Text type="secondary">Email</Text>
                        </div>
                        <Switch
                          checked={pref.email_enabled}
                          onChange={(checked) =>
                            updatePrefMutation.mutate({
                              type: pref.notification_type,
                              field: 'email_enabled',
                              value: checked,
                            })
                          }
                        />
                      </div>
                      <div className="text-center">
                        <div className="mb-1">
                          <Text type="secondary">Push</Text>
                        </div>
                        <Switch
                          checked={pref.push_enabled}
                          onChange={(checked) =>
                            updatePrefMutation.mutate({
                              type: pref.notification_type,
                              field: 'push_enabled',
                              value: checked,
                            })
                          }
                        />
                      </div>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default NotificationsPage

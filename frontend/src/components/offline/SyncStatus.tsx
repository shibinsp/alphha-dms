import React, { useEffect } from 'react'
import { Badge, Tooltip, Button, Popover, Progress, Space, Typography, message } from 'antd'
import {
  CloudOutlined,
  CloudSyncOutlined,
  DisconnectOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useOfflineStore } from '@/store/offlineStore'

const { Text } = Typography

const SyncStatus: React.FC = () => {
  const {
    isOnline,
    syncStatus,
    isSyncing,
    storageStats,
    processQueue,
    loadSyncStatus,
    loadStorageStats,
    clearOfflineData,
  } = useOfflineStore()

  // Refresh status periodically
  useEffect(() => {
    loadSyncStatus()
    loadStorageStats()

    const interval = setInterval(() => {
      loadSyncStatus()
    }, 30000) // Every 30 seconds

    return () => clearInterval(interval)
  }, [loadSyncStatus, loadStorageStats])

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  // Handle sync click
  const handleSync = async () => {
    if (!isOnline) {
      message.warning('You are offline. Changes will sync when you reconnect.')
      return
    }

    try {
      await processQueue()
      message.success('Sync completed!')
    } catch (error) {
      message.error('Sync failed. Will retry later.')
    }
  }

  // Handle clear data
  const handleClearData = async () => {
    try {
      await clearOfflineData()
      message.success('Offline data cleared')
    } catch (error) {
      message.error('Failed to clear offline data')
    }
  }

  // Determine status icon and color
  const getStatusIcon = () => {
    if (!isOnline) {
      return <DisconnectOutlined style={{ color: '#ff4d4f' }} />
    }
    if (isSyncing) {
      return <SyncOutlined spin style={{ color: '#1890ff' }} />
    }
    if (syncStatus.failed > 0) {
      return <ExclamationCircleOutlined style={{ color: '#faad14' }} />
    }
    if (syncStatus.pending > 0) {
      return <CloudSyncOutlined style={{ color: '#1890ff' }} />
    }
    return <CloudOutlined style={{ color: '#52c41a' }} />
  }

  // Determine badge count
  const getBadgeCount = () => {
    if (!isOnline) return undefined
    return syncStatus.pending + syncStatus.failed || undefined
  }

  // Popover content
  const popoverContent = (
    <div style={{ width: 280 }}>
      {/* Connection Status */}
      <div
        style={{
          padding: '8px 12px',
          background: isOnline ? '#f6ffed' : '#fff1f0',
          borderRadius: 6,
          marginBottom: 12,
        }}
      >
        <Space>
          {isOnline ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : (
            <DisconnectOutlined style={{ color: '#ff4d4f' }} />
          )}
          <Text strong>{isOnline ? 'Online' : 'Offline'}</Text>
        </Space>
        <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
          {isOnline
            ? 'All changes will sync automatically'
            : 'Changes will sync when reconnected'}
        </Text>
      </div>

      {/* Sync Status */}
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          Sync Queue
        </Text>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text>Pending</Text>
            <Text strong>{syncStatus.pending}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text>Failed</Text>
            <Text strong style={{ color: syncStatus.failed > 0 ? '#ff4d4f' : undefined }}>
              {syncStatus.failed}
            </Text>
          </div>
        </Space>
      </div>

      {/* Storage Stats */}
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          Offline Storage
        </Text>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text>Documents</Text>
            <Text strong>{storageStats.documentsCount}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text>Size</Text>
            <Text strong>{formatSize(storageStats.filesSize)}</Text>
          </div>
          <Progress
            percent={Math.min((storageStats.filesSize / (100 * 1024 * 1024)) * 100, 100)}
            size="small"
            showInfo={false}
            strokeColor="#1890ff"
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {formatSize(storageStats.filesSize)} of 100 MB used
          </Text>
        </Space>
      </div>

      {/* Actions */}
      <Space direction="vertical" style={{ width: '100%' }}>
        {syncStatus.pending > 0 && isOnline && (
          <Button
            type="primary"
            icon={<SyncOutlined spin={isSyncing} />}
            onClick={handleSync}
            loading={isSyncing}
            block
          >
            Sync Now
          </Button>
        )}
        {storageStats.documentsCount > 0 && (
          <Button icon={<DeleteOutlined />} onClick={handleClearData} danger block>
            Clear Offline Data
          </Button>
        )}
      </Space>
    </div>
  )

  return (
    <Popover
      content={popoverContent}
      title={
        <Space>
          {getStatusIcon()}
          <span>Sync Status</span>
        </Space>
      }
      trigger="click"
      placement="bottomRight"
    >
      <Tooltip title={isOnline ? 'Sync Status' : 'Offline Mode'}>
        <Badge count={getBadgeCount()} size="small" offset={[-2, 2]}>
          <Button
            type="text"
            icon={getStatusIcon()}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          />
        </Badge>
      </Tooltip>
    </Popover>
  )
}

export default SyncStatus

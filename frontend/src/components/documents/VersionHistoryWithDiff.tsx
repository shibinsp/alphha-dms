import React, { useState } from 'react'
import { Timeline, Tag, Button, Space, Typography, Select, Card, Alert, message } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  RollbackOutlined,
  DiffOutlined,
  UserOutlined,
  DownloadOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import dayjs from 'dayjs'
import type { DocumentVersion, LifecycleStatus } from '@/types'

const { Text } = Typography

interface VersionHistoryWithDiffProps {
  documentId: string
  versions: DocumentVersion[]
  lifecycleStatus: LifecycleStatus
  isWormLocked?: boolean
  onRestore?: (versionNumber: number) => void
  restoreLoading?: boolean
  onViewVersion?: (version: DocumentVersion) => void
}

const VersionHistoryWithDiff: React.FC<VersionHistoryWithDiffProps> = ({
  documentId,
  versions,
  lifecycleStatus,
  isWormLocked,
  onRestore,
  restoreLoading,
  onViewVersion,
}) => {
  const [compareVersion, setCompareVersion] = useState<number | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const isInReview = lifecycleStatus === 'REVIEW'

  // Fetch diff when comparing
  const { data: diffData, isLoading: diffLoading } = useQuery({
    queryKey: ['version-diff', documentId, compareVersion, selectedVersion],
    queryFn: async () => {
      const res = await api.get(`/versions/documents/${documentId}/versions/${compareVersion}/diff/${selectedVersion}`)
      return res.data
    },
    enabled: !!compareVersion && !!selectedVersion && compareVersion !== selectedVersion,
  })

  const handleDownloadVersion = async (version: DocumentVersion) => {
    try {
      const response = await api.get(`/documents/${documentId}/versions/${version.version_number}/download`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `v${version.version_number}_${documentId}`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      message.error('Failed to download version')
    }
  }

  const getChangeSummary = (version: DocumentVersion, prevVersion?: DocumentVersion) => {
    if (!prevVersion) return 'Initial version'
    const changes: string[] = []
    
    if (version.checksum_sha256 !== prevVersion.checksum_sha256) {
      changes.push('File updated')
    }
    if (version.metadata_snapshot && prevVersion.metadata_snapshot) {
      const metaChanges = Object.keys(version.metadata_snapshot).filter(
        k => version.metadata_snapshot![k] !== prevVersion.metadata_snapshot?.[k]
      )
      if (metaChanges.length > 0) {
        changes.push(`Metadata: ${metaChanges.join(', ')}`)
      }
    }
    return changes.length > 0 ? changes.join(' • ') : 'No changes detected'
  }

  const renderDiffValue = (value: any) => {
    if (value === null || value === undefined) return <span className="text-gray-400">empty</span>
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div>
      {/* Diff Viewer - Only show during REVIEW */}
      {isInReview && versions.length > 1 && (
        <Card size="small" className="mb-4" title={<><DiffOutlined /> Compare Versions</>}>
          <Space className="mb-3">
            <Select
              style={{ width: 180 }}
              placeholder="Compare from"
              value={compareVersion}
              onChange={setCompareVersion}
              allowClear
            >
              {versions.map((v) => (
                <Select.Option key={v.version_number} value={v.version_number}>
                  Version {v.version_number}
                </Select.Option>
              ))}
            </Select>
            <span>→</span>
            <Select
              style={{ width: 180 }}
              placeholder="Compare to"
              value={selectedVersion}
              onChange={setSelectedVersion}
              allowClear
            >
              {versions.map((v) => (
                <Select.Option key={v.version_number} value={v.version_number}>
                  Version {v.version_number} {v.is_current && '(Current)'}
                </Select.Option>
              ))}
            </Select>
          </Space>

          {diffLoading && <div className="text-center py-4">Loading diff...</div>}
          
          {diffData && (
            <div className="border rounded p-3 bg-gray-50">
              <Alert
                type={diffData.file_changed ? 'warning' : 'success'}
                message={diffData.file_changed ? 'File content changed' : 'File content identical'}
                className="mb-3"
                showIcon
              />
              
              {Object.keys(diffData.metadata_changes || {}).length > 0 ? (
                <div className="font-mono text-sm">
                  {Object.entries(diffData.metadata_changes).map(([key, change]: [string, any]) => (
                    <div key={key} className="py-2 border-b border-gray-200">
                      <strong className="w-32 inline-block">{key}:</strong>
                      <div className="ml-4">
                        <div className="bg-red-50 px-2 py-1 rounded inline-block mb-1">
                          <span className="text-red-600">- </span>
                          {renderDiffValue(change.from)}
                        </div>
                        <br />
                        <div className="bg-green-50 px-2 py-1 rounded inline-block">
                          <span className="text-green-600">+ </span>
                          {renderDiffValue(change.to)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Text type="secondary">No metadata changes</Text>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Version Timeline */}
      <Timeline
        items={versions.map((version, idx) => {
          const prevVersion = versions[idx + 1]
          return {
            color: version.is_current ? 'green' : 'gray',
            dot: version.is_current ? <CheckCircleOutlined /> : <ClockCircleOutlined />,
            children: (
              <div className="flex justify-between items-start pb-2">
                <div className="flex-1">
                  <Space>
                    <Text strong>Version {version.version_number}</Text>
                    {version.is_current && <Tag color="green">Current</Tag>}
                    {!version.is_current && <Tag color="default">Read-only</Tag>}
                  </Space>
                  
                  <div className="text-gray-500 text-sm mt-1">
                    <ClockCircleOutlined className="mr-1" />
                    {dayjs(version.created_at).format('MMM D, YYYY h:mm A')}
                    {version.creator && (
                      <span className="ml-3">
                        <UserOutlined className="mr-1" />
                        {version.creator.full_name || version.creator.email}
                      </span>
                    )}
                  </div>
                  
                  {version.change_reason && (
                    <div className="text-gray-600 mt-1 italic">"{version.change_reason}"</div>
                  )}
                  
                  {/* Changes summary */}
                  <div className="text-xs text-blue-600 mt-1">
                    {getChangeSummary(version, prevVersion)}
                  </div>
                </div>
                
                <Space size="small">
                  <Button
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => onViewVersion?.(version)}
                  >
                    View
                  </Button>
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    onClick={() => handleDownloadVersion(version)}
                  >
                    Download
                  </Button>
                  {!version.is_current && !isWormLocked && onRestore && (
                    <Button
                      size="small"
                      icon={<RollbackOutlined />}
                      onClick={() => onRestore(version.version_number)}
                      loading={restoreLoading}
                    >
                      Revert
                    </Button>
                  )}
                </Space>
              </div>
            ),
          }
        })}
      />
    </div>
  )
}

export default VersionHistoryWithDiff

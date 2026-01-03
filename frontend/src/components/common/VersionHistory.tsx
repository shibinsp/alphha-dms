import React from 'react'
import { Timeline, Tag, Button, Typography, Space, Tooltip, Empty } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  RollbackOutlined,
  DiffOutlined,
} from '@ant-design/icons'
import type { DocumentVersion } from '@/types'
import dayjs from 'dayjs'

const { Text } = Typography

interface VersionHistoryProps {
  versions: DocumentVersion[]
  onDownload?: (version: DocumentVersion) => void
  onRestore?: (version: DocumentVersion) => void
  onCompare?: (version1: DocumentVersion, version2: DocumentVersion) => void
}

const VersionHistory: React.FC<VersionHistoryProps> = ({
  versions,
  onDownload,
  onRestore,
  onCompare,
}) => {
  const [selectedForCompare, setSelectedForCompare] = React.useState<DocumentVersion | null>(null)

  if (!versions || versions.length === 0) {
    return <Empty description="No versions found" />
  }

  const handleCompareClick = (version: DocumentVersion) => {
    if (!selectedForCompare) {
      setSelectedForCompare(version)
    } else if (selectedForCompare.id === version.id) {
      setSelectedForCompare(null)
    } else {
      onCompare?.(selectedForCompare, version)
      setSelectedForCompare(null)
    }
  }

  const items = versions.map((version) => ({
    color: version.is_current ? 'green' : 'gray',
    dot: version.is_current ? (
      <CheckCircleOutlined style={{ fontSize: 16 }} />
    ) : (
      <ClockCircleOutlined style={{ fontSize: 16 }} />
    ),
    children: (
      <div className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <Space>
              <Text strong>Version {version.version_number}</Text>
              {version.is_current && (
                <Tag color="green" className="ml-1">Current</Tag>
              )}
              {selectedForCompare?.id === version.id && (
                <Tag color="blue">Selected for Compare</Tag>
              )}
            </Space>
            <div className="text-gray-500 text-sm mt-1">
              {dayjs(version.created_at).format('MMM D, YYYY h:mm A')}
            </div>
            {version.change_reason && (
              <div className="text-gray-600 mt-2 text-sm">
                <Text italic>"{version.change_reason}"</Text>
              </div>
            )}
            {version.file_size && (
              <div className="text-gray-400 text-xs mt-1">
                Size: {(version.file_size / 1024).toFixed(1)} KB
              </div>
            )}
          </div>
          <Space size="small">
            {onCompare && (
              <Tooltip title={selectedForCompare ? 'Compare with selected' : 'Select for compare'}>
                <Button
                  size="small"
                  icon={<DiffOutlined />}
                  onClick={() => handleCompareClick(version)}
                  type={selectedForCompare?.id === version.id ? 'primary' : 'default'}
                />
              </Tooltip>
            )}
            {onDownload && (
              <Tooltip title="Download this version">
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => onDownload(version)}
                />
              </Tooltip>
            )}
            {onRestore && !version.is_current && (
              <Tooltip title="Restore this version">
                <Button
                  size="small"
                  icon={<RollbackOutlined />}
                  onClick={() => onRestore(version)}
                />
              </Tooltip>
            )}
          </Space>
        </div>
      </div>
    ),
  }))

  return (
    <div>
      {selectedForCompare && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <Text type="secondary">
            Version {selectedForCompare.version_number} selected. Click another version to compare, or click the same version to deselect.
          </Text>
        </div>
      )}
      <Timeline items={items} />
    </div>
  )
}

export default VersionHistory

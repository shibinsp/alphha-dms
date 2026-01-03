import React, { useState, useCallback } from 'react'
import { Upload, message, Progress, Typography, Space } from 'antd'
import {
  InboxOutlined,
  FileOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import type { UploadProps } from 'antd'

const { Dragger } = Upload
const { Text } = Typography

interface FileUploaderProps {
  value?: File | null
  onChange?: (file: File | null) => void
  maxSize?: number // in MB
  accept?: string
  disabled?: boolean
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'text/csv',
  'text/plain',
]

const getFileIcon = (mimeType: string) => {
  if (mimeType.includes('pdf')) return <FilePdfOutlined className="text-red-500" />
  if (mimeType.includes('word') || mimeType.includes('document')) return <FileWordOutlined className="text-blue-500" />
  if (mimeType.includes('excel') || mimeType.includes('sheet')) return <FileExcelOutlined className="text-green-500" />
  if (mimeType.includes('image')) return <FileImageOutlined className="text-purple-500" />
  return <FileOutlined className="text-gray-500" />
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const FileUploader: React.FC<FileUploaderProps> = ({
  value,
  onChange,
  maxSize = 50,
  accept = '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.csv,.txt',
  disabled = false,
}) => {
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [isUploading, setIsUploading] = useState(false)

  const handleBeforeUpload = useCallback((file: File) => {
    // Check file type
    if (!ALLOWED_TYPES.includes(file.type)) {
      message.error('File type not supported. Please upload PDF, Word, Excel, Image, or CSV files.')
      return false
    }

    // Check file size
    const maxSizeBytes = maxSize * 1024 * 1024
    if (file.size > maxSizeBytes) {
      message.error(`File size exceeds ${maxSize}MB limit.`)
      return false
    }

    // Simulate upload progress for UX
    setIsUploading(true)
    setUploadProgress(0)

    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setIsUploading(false)
          return 100
        }
        return prev + 10
      })
    }, 50)

    onChange?.(file)
    return false // Prevent automatic upload
  }, [maxSize, onChange])

  const handleRemove = useCallback(() => {
    onChange?.(null)
    setUploadProgress(0)
    setIsUploading(false)
  }, [onChange])

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept,
    beforeUpload: handleBeforeUpload,
    onRemove: handleRemove,
    fileList: value ? [{
      uid: '1',
      name: value.name,
      status: 'done',
      size: value.size,
      type: value.type,
    }] : [],
    showUploadList: false,
    disabled,
  }

  if (value) {
    return (
      <div className="border border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">
        <div className="flex items-center gap-4">
          <div className="text-3xl">
            {getFileIcon(value.type)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Text strong className="truncate">{value.name}</Text>
              <CheckCircleOutlined className="text-green-500" />
            </div>
            <Text type="secondary" className="text-sm">
              {formatFileSize(value.size)}
            </Text>
            {isUploading && (
              <Progress percent={uploadProgress} size="small" className="mt-2" />
            )}
          </div>
          {!disabled && (
            <button
              onClick={handleRemove}
              className="p-2 hover:bg-gray-200 rounded transition-colors"
            >
              <DeleteOutlined className="text-gray-500 hover:text-red-500" />
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <Dragger {...uploadProps} className="bg-gray-50">
      <p className="ant-upload-drag-icon">
        <InboxOutlined style={{ color: '#1E3A5F' }} />
      </p>
      <p className="ant-upload-text">
        Click or drag file to this area to upload
      </p>
      <p className="ant-upload-hint">
        <Space direction="vertical" size={0}>
          <span>Supported formats: PDF, Word, Excel, Images, CSV</span>
          <span>Maximum file size: {maxSize}MB</span>
        </Space>
      </p>
    </Dragger>
  )
}

export default FileUploader

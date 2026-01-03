import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Upload,
  message,
  Typography,
  Space,
  Divider,
} from 'antd'
import {
  InboxOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { useQuery, useMutation } from '@tanstack/react-query'
import { documentService, UploadDocumentRequest } from '@/services/documentService'
import type { SourceType } from '@/types'

const { Title } = Typography
const { Option } = Select
const { Dragger } = Upload

interface UploadFormValues {
  title: string
  source_type: SourceType
  document_type_id: string
  customer_id?: string
  vendor_id?: string
  department_id?: string
  folder_id?: string
  classification: string
}

const DocumentUploadPage: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [file, setFile] = useState<File | null>(null)
  const sourceType = Form.useWatch('source_type', form)

  // Fetch document types
  const { data: documentTypes } = useQuery({
    queryKey: ['document-types'],
    queryFn: () => documentService.getDocumentTypes(),
  })

  // Fetch departments
  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => documentService.getDepartments(),
  })

  // Fetch folders
  const { data: folders } = useQuery({
    queryKey: ['folders'],
    queryFn: () => documentService.getFolders(),
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (data: UploadDocumentRequest) => documentService.uploadDocument(data),
    onSuccess: (document) => {
      message.success('Document uploaded successfully')
      navigate(`/documents/${document.id}`)
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || 'Upload failed')
    },
  })

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    beforeUpload: (file) => {
      setFile(file)
      return false // Prevent automatic upload
    },
    onRemove: () => {
      setFile(null)
    },
    fileList: file ? [{ uid: '1', name: file.name, status: 'done' }] : [],
  }

  const handleSubmit = async (values: UploadFormValues) => {
    if (!file) {
      message.error('Please select a file to upload')
      return
    }

    uploadMutation.mutate({
      file,
      title: values.title,
      source_type: values.source_type,
      document_type_id: values.document_type_id,
      customer_id: values.customer_id,
      vendor_id: values.vendor_id,
      department_id: values.department_id,
      folder_id: values.folder_id,
      classification: values.classification,
    })
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>
          Back
        </Button>
        <Title level={3} className="mb-0">
          Upload Document
        </Title>
      </div>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ classification: 'INTERNAL' }}
        >
          {/* File Upload */}
          <Form.Item
            label="Document File"
            required
            className="mb-6"
          >
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                Click or drag file to this area to upload
              </p>
              <p className="ant-upload-hint">
                Support for PDF, Word, Excel, Images, and CSV files. Max size: 50MB
              </p>
            </Dragger>
          </Form.Item>

          <Divider />

          {/* Document Details */}
          <Form.Item
            name="title"
            label="Document Title"
            rules={[{ required: true, message: 'Please enter a title' }]}
          >
            <Input placeholder="Enter document title" />
          </Form.Item>

          <Space className="w-full" size="large">
            <Form.Item
              name="source_type"
              label="Source Type"
              rules={[{ required: true, message: 'Please select source type' }]}
              className="flex-1"
            >
              <Select placeholder="Select source type">
                <Option value="CUSTOMER">Customer</Option>
                <Option value="VENDOR">Vendor</Option>
                <Option value="INTERNAL">Internal</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="document_type_id"
              label="Document Type"
              rules={[{ required: true, message: 'Please select document type' }]}
              className="flex-1"
            >
              <Select placeholder="Select document type">
                {documentTypes?.map((type) => (
                  <Option key={type.id} value={type.id}>
                    {type.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Space>

          {/* Conditional fields based on source type */}
          {sourceType === 'CUSTOMER' && (
            <Form.Item name="customer_id" label="Customer ID">
              <Input placeholder="Enter customer ID" />
            </Form.Item>
          )}

          {sourceType === 'VENDOR' && (
            <Form.Item name="vendor_id" label="Vendor ID">
              <Input placeholder="Enter vendor ID" />
            </Form.Item>
          )}

          {sourceType === 'INTERNAL' && (
            <Form.Item name="department_id" label="Department">
              <Select placeholder="Select department">
                {departments?.map((dept) => (
                  <Option key={dept.id} value={dept.id}>
                    {dept.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          )}

          <Space className="w-full" size="large">
            <Form.Item name="folder_id" label="Folder" className="flex-1">
              <Select placeholder="Select folder (optional)" allowClear>
                {folders?.map((folder) => (
                  <Option key={folder.id} value={folder.id}>
                    {folder.path}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="classification"
              label="Classification"
              rules={[{ required: true }]}
              className="flex-1"
            >
              <Select>
                <Option value="PUBLIC">Public</Option>
                <Option value="INTERNAL">Internal</Option>
                <Option value="CONFIDENTIAL">Confidential</Option>
                <Option value="RESTRICTED">Restricted</Option>
              </Select>
            </Form.Item>
          </Space>

          <Divider />

          <Form.Item className="mb-0">
            <Space>
              <Button onClick={() => navigate('/documents')}>
                Cancel
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={uploadMutation.isPending}
              >
                Upload Document
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default DocumentUploadPage

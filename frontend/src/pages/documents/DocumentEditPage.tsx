import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Form, Input, Upload, Button, message, Space, Typography, Spin, Alert, Tabs, Select, Divider } from 'antd'
import { UploadOutlined, ArrowLeftOutlined, SaveOutlined, FileOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentService } from '@/services/documentService'
import type { UploadFile } from 'antd/es/upload/interface'
import api from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input

const DocumentEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [metadataForm] = Form.useForm()
  const [versionForm] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [activeTab, setActiveTab] = useState('metadata')

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentService.getDocument(id!),
    enabled: !!id,
  })

  const { data: documentTypes } = useQuery({
    queryKey: ['document-types'],
    queryFn: () => documentService.getDocumentTypes(),
  })

  useEffect(() => {
    if (document) {
      metadataForm.setFieldsValue({
        title: document.title,
        classification: document.classification,
        document_type_id: document.document_type_id,
      })
    }
  }, [document, metadataForm])

  const updateMetadataMutation = useMutation({
    mutationFn: (values: { title: string; classification: string; document_type_id: string }) =>
      documentService.updateDocument(id!, values),
    onSuccess: () => {
      message.success('Document updated successfully')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      navigate(`/documents/${id}`)
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Failed to update document')
    }
  })

  const uploadVersionMutation = useMutation({
    mutationFn: async (values: { file: File; change_summary: string }) => {
      const formData = new FormData()
      formData.append('file', values.file)
      formData.append('change_summary', values.change_summary)
      const response = await api.post(`/documents/${id}/versions`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return response.data
    },
    onSuccess: () => {
      message.success('New version uploaded successfully')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      queryClient.invalidateQueries({ queryKey: ['document-versions', id] })
      navigate(`/documents/${id}`)
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Failed to upload new version')
    }
  })

  const handleMetadataSubmit = (values: { title: string; classification: string; document_type_id: string }) => {
    updateMetadataMutation.mutate(values)
  }

  const handleVersionSubmit = (values: { change_summary: string }) => {
    if (fileList.length === 0) {
      message.error('Please select a file to upload')
      return
    }
    const file = fileList[0].originFileObj as File
    uploadVersionMutation.mutate({ file, change_summary: values.change_summary })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (!document) {
    return <Alert type="error" message="Document not found" />
  }

  const tabItems = [
    {
      key: 'metadata',
      label: 'Edit Metadata',
      children: (
        <Form form={metadataForm} layout="vertical" onFinish={handleMetadataSubmit}>
          <Form.Item
            name="title"
            label="Title"
            rules={[{ required: true, message: 'Please enter a title' }]}
          >
            <Input placeholder="Document title" />
          </Form.Item>

          <Form.Item
            name="classification"
            label="Classification"
            rules={[{ required: true, message: 'Please select classification' }]}
          >
            <Select>
              <Select.Option value="PUBLIC">Public</Select.Option>
              <Select.Option value="INTERNAL">Internal</Select.Option>
              <Select.Option value="CONFIDENTIAL">Confidential</Select.Option>
              <Select.Option value="RESTRICTED">Restricted</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="document_type_id"
            label="Document Type"
            rules={[{ required: true, message: 'Please select document type' }]}
          >
            <Select>
              {documentTypes?.map((type) => (
                <Select.Option key={type.id} value={type.id}>{type.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={updateMetadataMutation.isPending}
              >
                Save Changes
              </Button>
              <Button onClick={() => navigate(`/documents/${id}`)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'version',
      label: 'Upload New Version',
      children: (
        <Form form={versionForm} layout="vertical" onFinish={handleVersionSubmit}>
          <div className="mb-4 p-3 bg-gray-50 rounded flex items-center gap-2">
            <FileOutlined />
            <Text>Current file: <Text strong>{document.file_name}</Text></Text>
          </div>

          <Form.Item label="New File" required>
            <Upload
              fileList={fileList}
              beforeUpload={(file) => {
                setFileList([{
                  uid: file.uid || '-1',
                  name: file.name,
                  status: 'done',
                  originFileObj: file,
                } as UploadFile])
                return false
              }}
              onRemove={() => setFileList([])}
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>Select File</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="change_summary"
            label="Change Summary"
            rules={[{ required: true, message: 'Please describe what changed' }]}
          >
            <TextArea rows={3} placeholder="Describe the changes in this version..." />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={uploadVersionMutation.isPending}
              >
                Upload New Version
              </Button>
              <Button onClick={() => navigate(`/documents/${id}`)}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      ),
    },
  ]

  return (
    <div className="p-6">
      <Card>
        <div className="mb-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/documents/${id}`)}>
            Back to Document
          </Button>
        </div>

        <Title level={4}>Edit Document</Title>
        <Text type="secondary" className="block mb-4">{document.title}</Text>

        <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />
      </Card>
    </div>
  )
}

export default DocumentEditPage

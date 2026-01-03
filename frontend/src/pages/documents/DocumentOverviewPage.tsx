import React, { useState, useEffect } from 'react';
import {
  Card, Descriptions, Tag, Space, Button, Image, Tabs, Table, Timeline,
  message, Spin, Alert, Modal, Form, Input, Select, DatePicker, Switch,
  Divider, Badge, Tooltip
} from 'antd';
import {
  FileTextOutlined, LockOutlined, UnlockOutlined, HistoryOutlined,
  ShareAltOutlined, EditOutlined, DownloadOutlined, EyeOutlined,
  UserOutlined, ShopOutlined, BankOutlined, TagsOutlined, DiffOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import VersionDiff from '../../components/common/VersionDiff';

interface DocumentDetail {
  id: string;
  title: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  page_count?: number;
  source_type: string;
  customer_id?: string;
  vendor_id?: string;
  department_id?: string;
  classification: string;
  lifecycle_status: string;
  is_worm_locked: boolean;
  legal_hold: boolean;
  retention_expiry?: string;
  ocr_status: string;
  custom_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface Version {
  id: string;
  version_number: number;
  file_size: number;
  change_reason?: string;
  is_current: boolean;
  created_at: string;
  created_by: string;
}

interface LockStatus {
  is_locked: boolean;
  locked_by?: string;
  locked_at?: string;
  reason?: string;
  is_mine?: boolean;
}

interface Permission {
  permission_level: string;
  can_view: boolean;
  can_download: boolean;
  can_edit: boolean;
  can_share: boolean;
  can_delete: boolean;
  is_masked: boolean;
}

const DocumentOverviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [lockStatus, setLockStatus] = useState<LockStatus | null>(null);
  const [permission, setPermission] = useState<Permission | null>(null);
  const [loading, setLoading] = useState(true);
  const [diffOpen, setDiffOpen] = useState(false);
  const [metadataModalOpen, setMetadataModalOpen] = useState(false);
  const [customFields, setCustomFields] = useState<any[]>([]);
  const [metadataForm] = Form.useForm();

  useEffect(() => {
    if (id) {
      fetchDocument();
      fetchVersions();
      fetchLockStatus();
      fetchPermission();
      fetchCustomFields();
    }
  }, [id]);

  const fetchDocument = async () => {
    try {
      const res = await api.get(`/documents/${id}`);
      setDocument(res.data);
    } catch (err) {
      message.error('Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const fetchVersions = async () => {
    try {
      const res = await api.get(`/documents/${id}/versions`);
      setVersions(res.data);
    } catch (err) {
      console.error('Failed to load versions');
    }
  };

  const fetchLockStatus = async () => {
    try {
      const res = await api.get(`/documents/${id}/lock-status`);
      setLockStatus(res.data);
    } catch (err) {
      console.error('Failed to load lock status');
    }
  };

  const fetchPermission = async () => {
    try {
      const res = await api.get(`/documents/${id}/my-permission`);
      setPermission(res.data);
    } catch (err) {
      console.error('Failed to load permission');
    }
  };

  const fetchCustomFields = async () => {
    try {
      const res = await api.get('/entities/custom-fields');
      setCustomFields(res.data);
    } catch (err) {
      console.error('Failed to load custom fields');
    }
  };

  const handleCheckout = async () => {
    try {
      await api.post(`/documents/${id}/checkout`, { reason: 'Editing document' });
      message.success('Document checked out');
      fetchLockStatus();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to checkout');
    }
  };

  const handleCheckin = async () => {
    try {
      await api.post(`/documents/${id}/checkin`, {});
      message.success('Document checked in');
      fetchLockStatus();
    } catch (err) {
      message.error('Failed to checkin');
    }
  };

  const handleRestoreVersion = async (versionNumber: number) => {
    try {
      await api.post(`/documents/${id}/restore/${versionNumber}`);
      message.success('Version restored');
      fetchDocument();
      fetchVersions();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to restore');
    }
  };

  const handleSaveMetadata = async (values: any) => {
    try {
      await api.patch(`/documents/${id}`, { custom_metadata: values });
      message.success('Metadata saved');
      setMetadataModalOpen(false);
      fetchDocument();
    } catch (err) {
      message.error('Failed to save metadata');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!document) {
    return <Alert type="error" message="Document not found" />;
  }

  const statusColors: Record<string, string> = {
    DRAFT: 'default',
    REVIEW: 'processing',
    APPROVED: 'success',
    ARCHIVED: 'warning',
    DELETED: 'error',
  };

  const sourceIcons: Record<string, React.ReactNode> = {
    CUSTOMER: <UserOutlined />,
    VENDOR: <ShopOutlined />,
    INTERNAL: <BankOutlined />,
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Space>
              <FileTextOutlined style={{ fontSize: 24 }} />
              <h2 style={{ margin: 0 }}>{document.title}</h2>
            </Space>
            <div style={{ marginTop: 8 }}>
              <Space>
                <Tag color={statusColors[document.lifecycle_status]}>{document.lifecycle_status}</Tag>
                <Tag icon={sourceIcons[document.source_type]}>{document.source_type}</Tag>
                <Tag color="blue">{document.classification}</Tag>
                {document.is_worm_locked && <Tag color="red" icon={<LockOutlined />}>WORM Locked</Tag>}
                {document.legal_hold && <Tag color="orange">Legal Hold</Tag>}
                {lockStatus?.is_locked && (
                  <Tag color="volcano" icon={<LockOutlined />}>
                    Checked out by {lockStatus.locked_by}
                  </Tag>
                )}
              </Space>
            </div>
          </div>
          <Space>
            {permission?.can_edit && !lockStatus?.is_locked && (
              <Button icon={<LockOutlined />} onClick={handleCheckout}>
                Check Out
              </Button>
            )}
            {lockStatus?.is_mine && (
              <Button icon={<UnlockOutlined />} onClick={handleCheckin}>
                Check In
              </Button>
            )}
            {permission?.can_download && (
              <Button icon={<DownloadOutlined />} type="primary">
                Download
              </Button>
            )}
            {permission?.can_share && (
              <Button icon={<ShareAltOutlined />}>Share</Button>
            )}
          </Space>
        </div>
      </Card>

      <Tabs
        items={[
          {
            key: 'overview',
            label: 'Overview',
            children: (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                {/* Document Preview */}
                <Card title="Preview" size="small">
                  <div
                    style={{
                      height: 300,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#fafafa',
                      borderRadius: 8,
                    }}
                  >
                    {document.mime_type.startsWith('image/') ? (
                      <Image
                        src={`/api/v1/documents/${id}/preview`}
                        style={{ maxHeight: 280 }}
                        fallback="data:image/png;base64,..."
                      />
                    ) : (
                      <div style={{ textAlign: 'center', color: '#888' }}>
                        <FileTextOutlined style={{ fontSize: 64 }} />
                        <p>{document.file_name}</p>
                        <p>{document.page_count ? `${document.page_count} pages` : ''}</p>
                      </div>
                    )}
                  </div>
                </Card>

                {/* Metadata */}
                <Card
                  title="Metadata"
                  size="small"
                  extra={
                    permission?.can_edit && (
                      <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => {
                          metadataForm.setFieldsValue(document.custom_metadata);
                          setMetadataModalOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                    )
                  }
                >
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="File Name">{document.file_name}</Descriptions.Item>
                    <Descriptions.Item label="Size">{formatFileSize(document.file_size)}</Descriptions.Item>
                    <Descriptions.Item label="Type">{document.mime_type}</Descriptions.Item>
                    <Descriptions.Item label="Pages">{document.page_count || 'N/A'}</Descriptions.Item>
                    <Descriptions.Item label="OCR Status">
                      <Tag color={document.ocr_status === 'COMPLETED' ? 'green' : 'default'}>
                        {document.ocr_status}
                      </Tag>
                    </Descriptions.Item>
                    {document.retention_expiry && (
                      <Descriptions.Item label="Retention Expiry">
                        {new Date(document.retention_expiry).toLocaleDateString()}
                      </Descriptions.Item>
                    )}
                  </Descriptions>

                  {Object.keys(document.custom_metadata || {}).length > 0 && (
                    <>
                      <Divider style={{ margin: '12px 0' }}>Custom Fields</Divider>
                      <Descriptions column={1} size="small">
                        {Object.entries(document.custom_metadata).map(([key, value]) => (
                          <Descriptions.Item key={key} label={key}>
                            {String(value)}
                          </Descriptions.Item>
                        ))}
                      </Descriptions>
                    </>
                  )}
                </Card>

                {/* Source Entity */}
                <Card title="Source Entity" size="small">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="Source Type">
                      <Tag icon={sourceIcons[document.source_type]}>{document.source_type}</Tag>
                    </Descriptions.Item>
                    {document.customer_id && (
                      <Descriptions.Item label="Customer ID">
                        <Tag color="blue">{document.customer_id}</Tag>
                      </Descriptions.Item>
                    )}
                    {document.vendor_id && (
                      <Descriptions.Item label="Vendor ID">
                        <Tag color="purple">{document.vendor_id}</Tag>
                      </Descriptions.Item>
                    )}
                    {document.department_id && (
                      <Descriptions.Item label="Department">
                        <Tag color="cyan">{document.department_id}</Tag>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>

                {/* Audit Info */}
                <Card title="Audit Information" size="small">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="Created">
                      {new Date(document.created_at).toLocaleString()}
                    </Descriptions.Item>
                    <Descriptions.Item label="Created By">{document.created_by}</Descriptions.Item>
                    <Descriptions.Item label="Last Updated">
                      {new Date(document.updated_at).toLocaleString()}
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              </div>
            ),
          },
          {
            key: 'versions',
            label: (
              <Space>
                <HistoryOutlined />
                Versions ({versions.length})
              </Space>
            ),
            children: (
              <Card
                extra={
                  versions.length >= 2 && (
                    <Button icon={<DiffOutlined />} onClick={() => setDiffOpen(true)}>
                      Compare Versions
                    </Button>
                  )
                }
              >
                <Table
                  dataSource={versions}
                  rowKey="id"
                  columns={[
                    {
                      title: 'Version',
                      dataIndex: 'version_number',
                      render: (v: number, record: Version) => (
                        <Space>
                          <Badge status={record.is_current ? 'success' : 'default'} />
                          v{v}
                          {record.is_current && <Tag color="green">Current</Tag>}
                        </Space>
                      ),
                    },
                    {
                      title: 'Size',
                      dataIndex: 'file_size',
                      render: (s: number) => formatFileSize(s),
                    },
                    {
                      title: 'Change Reason',
                      dataIndex: 'change_reason',
                      ellipsis: true,
                    },
                    {
                      title: 'Created',
                      dataIndex: 'created_at',
                      render: (d: string) => new Date(d).toLocaleString(),
                    },
                    {
                      title: 'Actions',
                      render: (_: any, record: Version) =>
                        !record.is_current &&
                        permission?.can_edit && (
                          <Button
                            type="link"
                            size="small"
                            onClick={() => handleRestoreVersion(record.version_number)}
                          >
                            Restore
                          </Button>
                        ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'permissions',
            label: (
              <Space>
                <ShareAltOutlined />
                Permissions
              </Space>
            ),
            children: (
              <Card>
                <Alert
                  type="info"
                  message={`Your permission level: ${permission?.permission_level}`}
                  style={{ marginBottom: 16 }}
                />
                <Descriptions column={2}>
                  <Descriptions.Item label="Can View">
                    {permission?.can_view ? '✓' : '✗'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Can Download">
                    {permission?.can_download ? '✓' : '✗'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Can Edit">
                    {permission?.can_edit ? '✓' : '✗'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Can Share">
                    {permission?.can_share ? '✓' : '✗'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Can Delete">
                    {permission?.can_delete ? '✓' : '✗'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Masked View">
                    {permission?.is_masked ? 'Yes' : 'No'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
        ]}
      />

      {/* Version Diff Modal */}
      <VersionDiff
        documentId={id!}
        versions={versions}
        open={diffOpen}
        onClose={() => setDiffOpen(false)}
      />

      {/* Custom Metadata Modal */}
      <Modal
        title="Edit Custom Metadata"
        open={metadataModalOpen}
        onCancel={() => setMetadataModalOpen(false)}
        onOk={() => metadataForm.submit()}
      >
        <Form form={metadataForm} layout="vertical" onFinish={handleSaveMetadata}>
          {customFields.map((field) => (
            <Form.Item
              key={field.field_key}
              name={field.field_key}
              label={field.name}
              rules={field.required ? [{ required: true }] : []}
            >
              {field.field_type === 'TEXT' && <Input />}
              {field.field_type === 'NUMBER' && <Input type="number" />}
              {field.field_type === 'DATE' && <DatePicker style={{ width: '100%' }} />}
              {field.field_type === 'SELECT' && (
                <Select options={field.options?.map((o: string) => ({ label: o, value: o }))} />
              )}
              {field.field_type === 'MULTI_SELECT' && (
                <Select
                  mode="multiple"
                  options={field.options?.map((o: string) => ({ label: o, value: o }))}
                />
              )}
              {field.field_type === 'BOOLEAN' && <Switch />}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentOverviewPage;

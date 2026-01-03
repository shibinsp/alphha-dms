import React, { useState, useEffect } from 'react';
import { Modal, Select, Card, Tag, Space, Spin, Alert, Descriptions, Badge } from 'antd';
import { DiffOutlined, SwapOutlined } from '@ant-design/icons';
import { api } from '../../services/api';

interface VersionDiffProps {
  documentId: string;
  versions: Array<{ version_number: number; created_at: string; created_by: string }>;
  open: boolean;
  onClose: () => void;
}

interface DiffResult {
  version_from: number;
  version_to: number;
  metadata_changes: Record<string, { from: any; to: any }>;
  file_changed: boolean;
  from_checksum: string;
  to_checksum: string;
}

const VersionDiff: React.FC<VersionDiffProps> = ({ documentId, versions, open, onClose }) => {
  const [fromVersion, setFromVersion] = useState<number | null>(null);
  const [toVersion, setToVersion] = useState<number | null>(null);
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (versions.length >= 2) {
      setFromVersion(versions[versions.length - 2]?.version_number);
      setToVersion(versions[versions.length - 1]?.version_number);
    }
  }, [versions]);

  useEffect(() => {
    if (fromVersion && toVersion && fromVersion !== toVersion) {
      fetchDiff();
    }
  }, [fromVersion, toVersion]);

  const fetchDiff = async () => {
    if (!fromVersion || !toVersion) return;
    setLoading(true);
    try {
      const res = await api.get(`/documents/${documentId}/versions/${fromVersion}/diff/${toVersion}`);
      setDiff(res.data);
    } catch (err) {
      console.error('Failed to fetch diff', err);
    } finally {
      setLoading(false);
    }
  };

  const renderDiffValue = (value: any) => {
    if (value === null || value === undefined) return <span style={{ color: '#999' }}>empty</span>;
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  return (
    <Modal
      title={
        <Space>
          <DiffOutlined />
          Version Comparison
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <Space style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 200 }}
          placeholder="From version"
          value={fromVersion}
          onChange={setFromVersion}
        >
          {versions.map((v) => (
            <Select.Option key={v.version_number} value={v.version_number}>
              Version {v.version_number} - {new Date(v.created_at).toLocaleDateString()}
            </Select.Option>
          ))}
        </Select>

        <SwapOutlined />

        <Select
          style={{ width: 200 }}
          placeholder="To version"
          value={toVersion}
          onChange={setToVersion}
        >
          {versions.map((v) => (
            <Select.Option key={v.version_number} value={v.version_number}>
              Version {v.version_number} - {new Date(v.created_at).toLocaleDateString()}
            </Select.Option>
          ))}
        </Select>
      </Space>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : diff ? (
        <div>
          {/* File Change Status */}
          <Alert
            type={diff.file_changed ? 'warning' : 'success'}
            message={
              diff.file_changed
                ? 'File content has changed between versions'
                : 'File content is identical'
            }
            style={{ marginBottom: 16 }}
            showIcon
          />

          {/* Metadata Changes */}
          <Card title="Metadata Changes" size="small">
            {Object.keys(diff.metadata_changes).length > 0 ? (
              <div style={{ fontFamily: 'monospace', fontSize: 13 }}>
                {Object.entries(diff.metadata_changes).map(([key, change]) => (
                  <div
                    key={key}
                    style={{
                      padding: '8px 12px',
                      borderBottom: '1px solid #f0f0f0',
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    <strong style={{ width: 150 }}>{key}:</strong>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          backgroundColor: '#fff1f0',
                          padding: '2px 8px',
                          borderRadius: 4,
                          marginBottom: 4,
                          display: 'inline-block',
                        }}
                      >
                        <span style={{ color: '#cf1322' }}>- </span>
                        {renderDiffValue(change.from)}
                      </div>
                      <br />
                      <div
                        style={{
                          backgroundColor: '#f6ffed',
                          padding: '2px 8px',
                          borderRadius: 4,
                          display: 'inline-block',
                        }}
                      >
                        <span style={{ color: '#389e0d' }}>+ </span>
                        {renderDiffValue(change.to)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>
                No metadata changes between these versions
              </p>
            )}
          </Card>

          {/* Checksums */}
          <Descriptions size="small" style={{ marginTop: 16 }} bordered column={1}>
            <Descriptions.Item label="From Checksum">
              <code style={{ fontSize: 11 }}>{diff.from_checksum}</code>
            </Descriptions.Item>
            <Descriptions.Item label="To Checksum">
              <code style={{ fontSize: 11 }}>{diff.to_checksum}</code>
            </Descriptions.Item>
          </Descriptions>
        </div>
      ) : (
        <Alert message="Select two different versions to compare" type="info" showIcon />
      )}
    </Modal>
  );
};

export default VersionDiff;

import React, { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Tabs, Descriptions, Tag, Card, Button, Space, Tooltip } from 'antd';
import {
  FileTextOutlined, DownloadOutlined, FullscreenOutlined,
  ZoomInOutlined, ZoomOutOutlined
} from '@ant-design/icons';
import api from '@/services/api';

interface DocumentViewerProps {
  documentId: string;
  fileName: string;
  mimeType: string;
  open: boolean;
  onClose: () => void;
  extractedMetadata?: Record<string, any>;
  ocrText?: string;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  fileName,
  mimeType,
  open,
  onClose,
  extractedMetadata,
  ocrText
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);
  const [fullscreen, setFullscreen] = useState(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);

  const isImage = mimeType?.startsWith('image/');
  const isPdf = mimeType === 'application/pdf';
  const isText = mimeType?.startsWith('text/') || 
    ['application/json', 'application/xml', 'application/javascript'].includes(mimeType);

  useEffect(() => {
    let currentBlobUrl: string | null = null;
    
    if (open && documentId) {
      setLoading(true);
      setError(null);
      setBlobUrl(null);
      setTextContent(null);
      
      // Fetch document with auth
      api.get(`/documents/${documentId}/preview`, { responseType: 'blob' })
        .then(async response => {
          // Check if response is actually an error (JSON instead of file)
          if (response.data.type === 'application/json') {
            const text = await response.data.text();
            const err = JSON.parse(text);
            throw new Error(err.detail || 'Failed to load document');
          }
          
          // For text files, read the content as text
          if (isText) {
            const text = await response.data.text();
            setTextContent(text);
          }
          
          currentBlobUrl = URL.createObjectURL(response.data);
          setBlobUrl(currentBlobUrl);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Preview error:', err);
          setError(err.message || 'Failed to load document');
          setLoading(false);
        });
    }
    
    return () => {
      if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
    };
  }, [open, documentId, isText]);

  const handleDownload = async () => {
    try {
      const response = await api.get(`/documents/${documentId}/download`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  };

  const handleZoomIn = () => setZoom(Math.min(zoom + 25, 200));
  const handleZoomOut = () => setZoom(Math.max(zoom - 25, 50));

  const renderViewer = () => {
    if (loading) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
          <Spin size="large" tip="Loading document..." />
        </div>
      );
    }

    if (error || !blobUrl) {
      return <Alert type="error" message={error || 'Failed to load document'} />;
    }

    if (isImage) {
      return (
        <div style={{ textAlign: 'center', overflow: 'auto', maxHeight: 600 }}>
          <img
            src={blobUrl}
            alt={fileName}
            style={{
              maxWidth: '100%',
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'top center',
            }}
          />
        </div>
      );
    }

    if (isPdf) {
      return (
        <iframe
          src={blobUrl}
          style={{
            width: '100%',
            height: fullscreen ? '90vh' : 600,
            border: 'none',
            borderRadius: 8
          }}
          title={fileName}
        />
      );
    }

    if (isText && textContent) {
      return (
        <Card style={{ maxHeight: 600, overflow: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.5 }}>
            {textContent}
          </pre>
        </Card>
      );
    }

    return (
      <Card style={{ maxHeight: 600, overflow: 'auto' }}>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
          {ocrText || 'No preview available for this file type.'}
        </pre>
      </Card>
    );
  };

  const renderMetadata = () => {
    if (!extractedMetadata || Object.keys(extractedMetadata).length === 0) {
      return <Alert type="info" message="No extracted metadata available" />;
    }

    const { entities, metadata, document_type, language, confidence } = extractedMetadata;

    return (
      <div style={{ maxHeight: 600, overflow: 'auto' }}>
        <Descriptions bordered size="small" column={1}>
          {document_type && (
            <Descriptions.Item label="Document Type">
              <Tag color="blue">{document_type}</Tag>
            </Descriptions.Item>
          )}
          {language && (
            <Descriptions.Item label="Language">
              <Tag>{language.toUpperCase()}</Tag>
            </Descriptions.Item>
          )}
          {confidence !== undefined && (
            <Descriptions.Item label="Confidence">
              <Tag color={confidence > 80 ? 'green' : confidence > 50 ? 'orange' : 'red'}>
                {confidence}%
              </Tag>
            </Descriptions.Item>
          )}
        </Descriptions>

        {entities && Object.keys(entities).length > 0 && (
          <Card title="Extracted Entities" size="small" style={{ marginTop: 16 }}>
            {entities.names?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong>Names:</strong>{' '}
                {entities.names.map((n: string, i: number) => <Tag key={i} color="purple">{n}</Tag>)}
              </div>
            )}
            {entities.dates?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong>Dates:</strong>{' '}
                {entities.dates.map((d: string, i: number) => <Tag key={i} color="cyan">{d}</Tag>)}
              </div>
            )}
            {entities.amounts?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong>Amounts:</strong>{' '}
                {entities.amounts.map((a: string, i: number) => <Tag key={i} color="green">{a}</Tag>)}
              </div>
            )}
            {entities.organizations?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong>Organizations:</strong>{' '}
                {entities.organizations.map((o: string, i: number) => <Tag key={i} color="orange">{o}</Tag>)}
              </div>
            )}
            {entities.id_numbers?.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong>ID Numbers:</strong>{' '}
                {entities.id_numbers.map((id: string, i: number) => <Tag key={i} color="red">{id}</Tag>)}
              </div>
            )}
          </Card>
        )}

        {metadata && Object.keys(metadata).length > 0 && (
          <Card title="Document Metadata" size="small" style={{ marginTop: 16 }}>
            <Descriptions size="small" column={1}>
              {metadata.title && <Descriptions.Item label="Title">{metadata.title}</Descriptions.Item>}
              {metadata.author && <Descriptions.Item label="Author">{metadata.author}</Descriptions.Item>}
              {metadata.subject && <Descriptions.Item label="Subject">{metadata.subject}</Descriptions.Item>}
            </Descriptions>
          </Card>
        )}
      </div>
    );
  };

  const renderOcrText = () => {
    // For text files, show the actual content
    if (isText && textContent) {
      return (
        <Card style={{ maxHeight: 600, overflow: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.5 }}>
            {textContent}
          </pre>
        </Card>
      );
    }
    
    if (!ocrText) {
      return <Alert type="info" message="No OCR text available" />;
    }

    return (
      <Card style={{ maxHeight: 600, overflow: 'auto' }}>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 14, lineHeight: 1.6 }}>
          {ocrText}
        </pre>
      </Card>
    );
  };

  return (
    <Modal
      title={<Space><FileTextOutlined />{fileName}</Space>}
      open={open}
      onCancel={onClose}
      width={fullscreen ? '95vw' : 900}
      style={fullscreen ? { top: 20 } : undefined}
      footer={
        <Space>
          <Tooltip title="Zoom Out">
            <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} disabled={zoom <= 50} />
          </Tooltip>
          <span>{zoom}%</span>
          <Tooltip title="Zoom In">
            <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} disabled={zoom >= 200} />
          </Tooltip>
          <Tooltip title="Fullscreen">
            <Button icon={<FullscreenOutlined />} onClick={() => setFullscreen(!fullscreen)} />
          </Tooltip>
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
            Download
          </Button>
        </Space>
      }
    >
      <Tabs
        items={[
          { key: 'preview', label: 'Preview', children: renderViewer() },
          { key: 'metadata', label: 'Extracted Data', children: renderMetadata() },
          { key: 'ocr', label: 'OCR Text', children: renderOcrText() }
        ]}
      />
    </Modal>
  );
};

export default DocumentViewer;

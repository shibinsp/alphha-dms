import React, { useState } from 'react'
import {
  Tag,
  Select,
  Button,
  Space,
  message,
  Spin,
  Empty,
  Typography,
  Badge,
  Tooltip,
  Card,
  Divider,
} from 'antd'
import {
  PlusOutlined,
  RobotOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  TagOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { taggingService, type Tag as TagType } from '@/services/taggingService'

const { Text } = Typography

interface DocumentTagsProps {
  documentId: string
  editable?: boolean
}

const TAG_COLORS = [
  'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'gold', 'lime', 'geekblue', 'volcano',
]

const getTagColor = (tag: TagType, index: number): string => {
  if (tag.color) return tag.color
  return TAG_COLORS[index % TAG_COLORS.length]
}

const DocumentTags: React.FC<DocumentTagsProps> = ({ documentId, editable = true }) => {
  const queryClient = useQueryClient()
  const [selectedTagId, setSelectedTagId] = useState<string | null>(null)
  const [isAutoTagging, setIsAutoTagging] = useState(false)

  // Fetch document tags
  const { data: documentTags = [], isLoading: tagsLoading } = useQuery({
    queryKey: ['document-tags', documentId],
    queryFn: () => taggingService.getDocumentTags(documentId),
  })

  // Fetch all available tags
  const { data: allTags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: () => taggingService.getTags(),
  })

  // Fetch suggestions for this document
  const { data: suggestions = [] } = useQuery({
    queryKey: ['tag-suggestions', documentId],
    queryFn: () => taggingService.getPendingSuggestions(documentId),
  })

  // Add tag mutation
  const addTagMutation = useMutation({
    mutationFn: (tagId: string) => taggingService.addTagToDocument(documentId, tagId),
    onSuccess: () => {
      message.success('Tag added')
      queryClient.invalidateQueries({ queryKey: ['document-tags', documentId] })
      setSelectedTagId(null)
    },
    onError: () => {
      message.error('Failed to add tag')
    },
  })

  // Remove tag mutation
  const removeTagMutation = useMutation({
    mutationFn: (tagId: string) => taggingService.removeTagFromDocument(documentId, tagId),
    onSuccess: () => {
      message.success('Tag removed')
      queryClient.invalidateQueries({ queryKey: ['document-tags', documentId] })
    },
    onError: () => {
      message.error('Failed to remove tag')
    },
  })

  // Auto-tag mutation
  const autoTagMutation = useMutation({
    mutationFn: () => taggingService.autoTagDocument(documentId),
    onSuccess: (data) => {
      setIsAutoTagging(false)
      if (data.length > 0) {
        message.success(`Found ${data.length} tag suggestions`)
        queryClient.invalidateQueries({ queryKey: ['tag-suggestions', documentId] })
      } else {
        message.info('No tags could be extracted from this document')
      }
    },
    onError: () => {
      setIsAutoTagging(false)
      message.error('Auto-tagging failed')
    },
  })

  // Approve suggestion mutation
  const approveMutation = useMutation({
    mutationFn: (suggestionId: string) => taggingService.approveSuggestion(suggestionId),
    onSuccess: () => {
      message.success('Suggestion approved')
      queryClient.invalidateQueries({ queryKey: ['document-tags', documentId] })
      queryClient.invalidateQueries({ queryKey: ['tag-suggestions', documentId] })
    },
    onError: () => {
      message.error('Failed to approve suggestion')
    },
  })

  // Reject suggestion mutation
  const rejectMutation = useMutation({
    mutationFn: (suggestionId: string) => taggingService.rejectSuggestion(suggestionId),
    onSuccess: () => {
      message.success('Suggestion rejected')
      queryClient.invalidateQueries({ queryKey: ['tag-suggestions', documentId] })
    },
    onError: () => {
      message.error('Failed to reject suggestion')
    },
  })

  const handleAutoTag = () => {
    setIsAutoTagging(true)
    autoTagMutation.mutate()
  }

  // Filter out already added tags
  const existingTagIds = documentTags.map((dt) => dt.tag_id)
  const availableTags = allTags.filter((t) => !existingTagIds.includes(t.id))

  if (tagsLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spin />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Current Tags */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <Text strong>
            <TagOutlined className="mr-2" />
            Tags ({documentTags.length})
          </Text>
          {editable && (
            <Button
              type="link"
              icon={<RobotOutlined />}
              onClick={handleAutoTag}
              loading={isAutoTagging || autoTagMutation.isPending}
              size="small"
            >
              Auto-Tag
            </Button>
          )}
        </div>

        {documentTags.length === 0 ? (
          <Empty
            description="No tags"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            className="py-4"
          />
        ) : (
          <Space wrap>
            {documentTags.map((docTag, index) => (
              <Tag
                key={docTag.id}
                color={getTagColor(docTag.tag, index)}
                closable={editable}
                onClose={(e) => {
                  e.preventDefault()
                  removeTagMutation.mutate(docTag.tag_id)
                }}
              >
                <Space size={4}>
                  {docTag.tag.name}
                  {docTag.tag_type === 'AUTO' && (
                    <Tooltip title={`Auto-tagged (${Math.round((docTag.confidence_score || 0) * 100)}% confidence)`}>
                      <RobotOutlined style={{ fontSize: 10 }} />
                    </Tooltip>
                  )}
                </Space>
              </Tag>
            ))}
          </Space>
        )}
      </div>

      {/* Add Tag */}
      {editable && (
        <div>
          <Text type="secondary" className="mb-2 block">Add Tag</Text>
          <Space>
            <Select
              showSearch
              placeholder="Select or search tags"
              value={selectedTagId}
              onChange={setSelectedTagId}
              style={{ width: 200 }}
              options={availableTags.map((t) => ({
                value: t.id,
                label: (
                  <Space>
                    <span>{t.name}</span>
                    {t.category && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        ({t.category})
                      </Text>
                    )}
                  </Space>
                ),
              }))}
              filterOption={(input, option) =>
                (option?.label as any)?.props?.children?.[0]?.props?.children
                  ?.toLowerCase()
                  ?.includes(input.toLowerCase()) ?? false
              }
              allowClear
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => selectedTagId && addTagMutation.mutate(selectedTagId)}
              disabled={!selectedTagId}
              loading={addTagMutation.isPending}
            >
              Add
            </Button>
          </Space>
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <>
          <Divider />
          <div>
            <Text strong className="mb-2 block">
              <BulbOutlined className="mr-2" />
              Suggestions ({suggestions.length})
            </Text>
            <Space wrap>
              {suggestions.map((suggestion) => (
                <Badge
                  key={suggestion.id}
                  count={`${Math.round(suggestion.confidence_score * 100)}%`}
                  size="small"
                  style={{ backgroundColor: suggestion.confidence_score > 0.8 ? '#52c41a' : '#faad14' }}
                >
                  <Card size="small" className="mb-1">
                    <Space>
                      <Text>{suggestion.suggested_tag_name}</Text>
                      {editable && (
                        <>
                          <Tooltip title="Approve">
                            <Button
                              type="text"
                              size="small"
                              icon={<CheckOutlined style={{ color: '#52c41a' }} />}
                              onClick={() => approveMutation.mutate(suggestion.id)}
                              loading={approveMutation.isPending}
                            />
                          </Tooltip>
                          <Tooltip title="Reject">
                            <Button
                              type="text"
                              size="small"
                              icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                              onClick={() => rejectMutation.mutate(suggestion.id)}
                              loading={rejectMutation.isPending}
                            />
                          </Tooltip>
                        </>
                      )}
                    </Space>
                  </Card>
                </Badge>
              ))}
            </Space>
          </div>
        </>
      )}
    </div>
  )
}

export default DocumentTags

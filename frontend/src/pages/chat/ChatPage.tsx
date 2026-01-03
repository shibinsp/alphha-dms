import React, { useState, useRef, useEffect } from 'react'
import {
  Input,
  Button,
  Typography,
  Avatar,
  Spin,
  Empty,
  Dropdown,
  message,
  Tag,
  Tooltip,
} from 'antd'
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  PlusOutlined,
  DeleteOutlined,
  FileOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import api from '@/services/api'

dayjs.extend(relativeTime)

const { Text, Paragraph, Title } = Typography
const { TextArea } = Input

interface ChatMessage {
  id: string
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  citations?: Array<{
    document_id: string
    chunk_text: string
    relevance_score: number
  }>
  created_at: string
  feedback?: string
}

interface ChatSession {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

const ChatPage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  // Fetch sessions
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: async () => {
      const response = await api.get('/chat/sessions')
      return response.data as ChatSession[]
    },
  })

  // Fetch active session
  const { data: activeSession, isLoading: sessionLoading } = useQuery({
    queryKey: ['chat-session', activeSessionId],
    queryFn: async () => {
      if (!activeSessionId) return null
      const response = await api.get(`/chat/sessions/${activeSessionId}`)
      return response.data as ChatSession
    },
    enabled: !!activeSessionId,
  })

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/chat/sessions', {})
      return response.data
    },
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setActiveSessionId(session.id)
    },
  })

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const response = await api.post(`/chat/sessions/${activeSessionId}/messages`, {
        message,
      })
      return response.data
    },
    onMutate: () => {
      setIsTyping(true)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-session', activeSessionId] })
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    },
    onSettled: () => {
      setIsTyping(false)
    },
  })

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      await api.delete(`/chat/sessions/${sessionId}`)
    },
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
      }
      message.success('Conversation deleted')
    },
  })

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: async ({ messageId, feedback }: { messageId: string; feedback: string }) => {
      await api.post(`/chat/messages/${messageId}/feedback`, { feedback })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-session', activeSessionId] })
      message.success('Thank you for your feedback')
    },
  })

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeSession?.messages])

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return

    if (!activeSessionId) {
      // Create new session first
      createSessionMutation.mutate(undefined, {
        onSuccess: (session) => {
          setActiveSessionId(session.id)
          sendMessageMutation.mutate(inputMessage)
        },
      })
    } else {
      sendMessageMutation.mutate(inputMessage)
    }

    setInputMessage('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex h-[calc(100vh-180px)]">
      {/* Sidebar - Session List */}
      <div className="w-64 border-r bg-gray-50 flex flex-col">
        <div className="p-4 border-b">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => createSessionMutation.mutate()}
            loading={createSessionMutation.isPending}
          >
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-auto p-2">
          {sessionsLoading ? (
            <div className="flex justify-center py-4">
              <Spin />
            </div>
          ) : sessions?.length ? (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-3 rounded-lg cursor-pointer hover:bg-gray-100 ${
                    activeSessionId === session.id ? 'bg-blue-50 border border-blue-200' : ''
                  }`}
                  onClick={() => setActiveSessionId(session.id)}
                >
                  <div className="flex justify-between items-start">
                    <Text
                      className="font-medium truncate flex-1"
                      style={{ maxWidth: '160px' }}
                    >
                      {session.title}
                    </Text>
                    <Dropdown
                      menu={{
                        items: [
                          {
                            key: 'delete',
                            icon: <DeleteOutlined />,
                            label: 'Delete',
                            danger: true,
                            onClick: (e) => {
                              e.domEvent.stopPropagation()
                              deleteSessionMutation.mutate(session.id)
                            },
                          },
                        ],
                      }}
                      trigger={['click']}
                    >
                      <Button
                        type="text"
                        size="small"
                        onClick={(e) => e.stopPropagation()}
                      >
                        •••
                      </Button>
                    </Dropdown>
                  </div>
                  <Text type="secondary" className="text-xs">
                    {dayjs(session.updated_at).fromNow()}
                  </Text>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4">
              <Text type="secondary">No conversations yet</Text>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {activeSessionId ? (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-auto p-4">
              {sessionLoading ? (
                <div className="flex justify-center py-12">
                  <Spin size="large" />
                </div>
              ) : activeSession?.messages?.length ? (
                <div className="space-y-4 max-w-3xl mx-auto">
                  {activeSession.messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${
                        msg.role === 'USER' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {msg.role === 'ASSISTANT' && (
                        <Avatar
                          icon={<RobotOutlined />}
                          style={{ backgroundColor: '#1E3A5F' }}
                        />
                      )}
                      <div
                        className={`max-w-[70%] ${
                          msg.role === 'USER'
                            ? 'bg-primary-500 text-white rounded-2xl rounded-tr-sm px-4 py-2'
                            : 'bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2'
                        }`}
                      >
                        <Paragraph
                          className={`mb-0 ${msg.role === 'USER' ? 'text-white' : ''}`}
                          style={{ whiteSpace: 'pre-wrap' }}
                        >
                          {msg.content}
                        </Paragraph>

                        {/* Citations */}
                        {msg.role === 'ASSISTANT' && msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3 pt-2 border-t border-gray-200">
                            <Text type="secondary" className="text-xs">
                              Sources:
                            </Text>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {msg.citations.map((citation, i) => (
                                <Tag
                                  key={i}
                                  icon={<FileOutlined />}
                                  className="cursor-pointer"
                                  onClick={() => navigate(`/documents/${citation.document_id}`)}
                                >
                                  Document {i + 1}
                                </Tag>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Feedback */}
                        {msg.role === 'ASSISTANT' && !msg.feedback && (
                          <div className="mt-2 flex gap-2">
                            <Tooltip title="Helpful">
                              <Button
                                type="text"
                                size="small"
                                icon={<LikeOutlined />}
                                onClick={() =>
                                  feedbackMutation.mutate({
                                    messageId: msg.id,
                                    feedback: 'HELPFUL',
                                  })
                                }
                              />
                            </Tooltip>
                            <Tooltip title="Not helpful">
                              <Button
                                type="text"
                                size="small"
                                icon={<DislikeOutlined />}
                                onClick={() =>
                                  feedbackMutation.mutate({
                                    messageId: msg.id,
                                    feedback: 'NOT_HELPFUL',
                                  })
                                }
                              />
                            </Tooltip>
                          </div>
                        )}
                      </div>
                      {msg.role === 'USER' && (
                        <Avatar icon={<UserOutlined />} />
                      )}
                    </div>
                  ))}

                  {isTyping && (
                    <div className="flex gap-3">
                      <Avatar
                        icon={<RobotOutlined />}
                        style={{ backgroundColor: '#1E3A5F' }}
                      />
                      <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2">
                        <Text type="secondary">Thinking...</Text>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <Empty description="Start a conversation" />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="border-t p-4">
              <div className="max-w-3xl mx-auto flex gap-2">
                <TextArea
                  placeholder="Ask about your documents..."
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={sendMessageMutation.isPending}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSendMessage}
                  loading={sendMessageMutation.isPending}
                  disabled={!inputMessage.trim()}
                />
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center">
            <RobotOutlined style={{ fontSize: 64, color: '#1E3A5F' }} />
            <Title level={4} className="mt-4">
              Alphha AI Assistant
            </Title>
            <Paragraph type="secondary" className="text-center max-w-md">
              Ask questions about your documents. The AI will search through your
              document library and provide answers with citations.
            </Paragraph>
            <Button
              type="primary"
              size="large"
              icon={<PlusOutlined />}
              onClick={() => createSessionMutation.mutate()}
              loading={createSessionMutation.isPending}
            >
              Start New Conversation
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatPage

import { useState } from 'react'
import { Modal, Select, Input, message } from 'antd'
import { accessRequestService, RequestedPermission } from '@/services/accessRequestService'

const { TextArea } = Input

interface Props {
  visible: boolean
  documentId: string
  documentTitle: string
  onClose: () => void
  onSuccess?: () => void
}

const permissionOptions = [
  { value: 'VIEW', label: 'View Only' },
  { value: 'DOWNLOAD', label: 'View & Download' },
  { value: 'EDIT', label: 'Edit' },
]

export default function RequestAccessModal({ visible, documentId, documentTitle, onClose, onSuccess }: Props) {
  const [permission, setPermission] = useState<RequestedPermission>('VIEW')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    setLoading(true)
    try {
      await accessRequestService.createRequest(documentId, permission, reason || undefined)
      message.success('Access request submitted')
      onClose()
      onSuccess?.()
      setPermission('VIEW')
      setReason('')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      message.error(error.response?.data?.detail || 'Failed to submit request')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="Request Access"
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={loading}
      okText="Submit Request"
    >
      <p className="mb-4">Request access to: <strong>{documentTitle}</strong></p>
      
      <div className="mb-4">
        <label className="block mb-2">Permission needed:</label>
        <Select
          className="w-full"
          value={permission}
          onChange={setPermission}
          options={permissionOptions}
        />
      </div>

      <div>
        <label className="block mb-2">Reason (optional):</label>
        <TextArea
          rows={3}
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="Why do you need access to this document?"
        />
      </div>
    </Modal>
  )
}

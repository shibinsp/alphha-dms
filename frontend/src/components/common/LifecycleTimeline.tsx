import React from 'react';
import { Steps, Tag } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, EditOutlined, FileSearchOutlined, InboxOutlined, DeleteOutlined } from '@ant-design/icons';

interface LifecycleTimelineProps {
  currentStatus: string;
  showLabels?: boolean;
}

const LIFECYCLE_STEPS = [
  { key: 'DRAFT', label: 'Draft', icon: <EditOutlined /> },
  { key: 'REVIEW', label: 'Review', icon: <FileSearchOutlined /> },
  { key: 'APPROVED', label: 'Approved', icon: <CheckCircleOutlined /> },
  { key: 'ARCHIVED', label: 'Archived', icon: <InboxOutlined /> },
];

const getStatusIndex = (status: string): number => {
  const idx = LIFECYCLE_STEPS.findIndex(s => s.key === status);
  return idx >= 0 ? idx : 0;
};

const LifecycleTimeline: React.FC<LifecycleTimelineProps> = ({ currentStatus, showLabels = true }) => {
  const currentIndex = getStatusIndex(currentStatus);
  const isDeleted = currentStatus === 'DELETED';

  if (isDeleted) {
    return (
      <div className="flex items-center gap-2">
        <Tag icon={<DeleteOutlined />} color="red">DELETED</Tag>
      </div>
    );
  }

  return (
    <Steps
      current={currentIndex}
      size="small"
      items={LIFECYCLE_STEPS.map((step, idx) => ({
        title: showLabels ? step.label : undefined,
        icon: step.icon,
        status: idx < currentIndex ? 'finish' : idx === currentIndex ? 'process' : 'wait',
      }))}
    />
  );
};

export default LifecycleTimeline;

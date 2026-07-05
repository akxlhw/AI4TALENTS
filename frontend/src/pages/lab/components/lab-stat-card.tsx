import { Card, Statistic } from 'antd'
import type { ReactNode } from 'react'

interface LabStatCardProps {
  title: string
  value: number
  icon: ReactNode
}

const LabStatCard: React.FC<LabStatCardProps> = ({ title, value, icon }) => {
  return (
    <Card
      style={{
        height: '100%',
        borderRadius: 12,
        transition: 'all 0.2s ease',
      }}
      styles={{ body: { display: 'flex', alignItems: 'center', gap: 16 } }}
      hoverable
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 12,
          background: 'var(--domain-light-bg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
          color: 'var(--domain-primary)',
        }}
      >
        {icon}
      </div>
      <Statistic title={title} value={value} valueStyle={{ fontSize: 32, fontWeight: 700, color: '#1a202c' }} />
    </Card>
  )
}

export default LabStatCard

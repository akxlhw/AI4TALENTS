import { Avatar, Tag, Typography, Space, Button } from 'antd'
import { MailOutlined, HomeOutlined } from '@ant-design/icons'
import type { LabTalentDetail } from '../../../types'
import { domainThemes } from '../../../theme'
import { ROLE_LABELS, LEVEL_LABELS } from '../constants/lab-role'

const { Title, Text } = Typography
const dt = domainThemes.lab

interface LabTalentHeaderProps {
  talent: LabTalentDetail
}

const LabTalentHeader: React.FC<LabTalentHeaderProps> = ({ talent }) => {
  const initials = talent.name.slice(0, 1)

  return (
    <div style={{ textAlign: 'center' }}>
      <Avatar
        size={120}
        src={talent.photo_url || undefined}
        style={{
          background: dt.gradient,
          color: '#fff',
          fontSize: 48,
          fontWeight: 700,
          marginBottom: 16,
        }}
      >
        {initials}
      </Avatar>
      <Title level={3} style={{ marginBottom: 8 }}>
        {talent.name}
      </Title>
      <Space size={8} wrap style={{ justifyContent: 'center', marginBottom: 8 }}>
        <Tag color="processing">{ROLE_LABELS[talent.role_type] || talent.role_type}</Tag>
        {talent.academic_level && (
          <Tag color="blue">{LEVEL_LABELS[talent.academic_level] || talent.academic_level}</Tag>
        )}
      </Space>
      {talent.current_title && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          {talent.current_title}
        </Text>
      )}
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {talent.email && (
          <Button icon={<MailOutlined />} href={`mailto:${talent.email}`} block>
            {talent.email}
          </Button>
        )}
        {talent.homepage && (
          <Button icon={<HomeOutlined />} href={talent.homepage} target="_blank" block>
            个人主页
          </Button>
        )}
      </Space>
    </div>
  )
}

export default LabTalentHeader

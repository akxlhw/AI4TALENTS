import { Avatar, Tag, Typography, Space, Button, Tooltip } from 'antd'
import {
  MailOutlined,
  HomeOutlined,
  GithubOutlined,
  LinkedinOutlined,
  TwitterOutlined,
  BookOutlined,
  IdcardOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import type { LabTalentDetail } from '../../../types'
import { domainThemes } from '../../../theme'
import { ROLE_LABELS, LEVEL_LABELS } from '../constants/lab-role'

const { Title, Text } = Typography
const dt = domainThemes.lab

// Platform key (lowercase, as stored in social_links) → icon + display label
const SOCIAL_ICONS: Record<string, React.ReactNode> = {
  linkedin: <LinkedinOutlined />,
  github: <GithubOutlined />,
  twitter: <TwitterOutlined />,
  x: <TwitterOutlined />,
  scholar: <BookOutlined />,
  google_scholar: <BookOutlined />,
  orcid: <IdcardOutlined />,
}

const SOCIAL_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  github: 'GitHub',
  twitter: 'Twitter',
  x: 'X',
  scholar: 'Google Scholar',
  google_scholar: 'Google Scholar',
  orcid: 'ORCID',
}

// Backend-generated Google search URLs stand in for profiles the crawler
// did not find — label them as search links so users can tell the difference.
const isSearchFallback = (url: string) => url.includes('google.com/search')

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
      {talent.social_links && Object.keys(talent.social_links).length > 0 && (
        <Space size={8} wrap style={{ justifyContent: 'center', marginTop: 12 }}>
          {Object.entries(talent.social_links).map(([platform, url]) => {
            const label = SOCIAL_LABELS[platform] || platform
            return (
              <Tooltip key={platform} title={isSearchFallback(url) ? `${label}（搜索）` : label}>
                <Button
                  shape="circle"
                  icon={SOCIAL_ICONS[platform] || <LinkOutlined />}
                  href={url}
                  target="_blank"
                />
              </Tooltip>
            )
          })}
        </Space>
      )}
    </div>
  )
}

export default LabTalentHeader

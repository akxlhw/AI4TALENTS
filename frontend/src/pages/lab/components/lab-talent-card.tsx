import { Card, Tag, Typography, Space, Avatar } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { LabTalent } from '../../../types'
import { domainThemes } from '../../../theme'

const { Text } = Typography
const dt = domainThemes.lab

const ROLE_LABELS: Record<string, string> = {
  professor: '教授',
  student: '学生',
  graduate: '博后/研究员',
  unknown: '其他',
}

const LEVEL_LABELS: Record<string, string> = {
  phd: '博士',
  master: '硕士',
  bachelor: '学士',
}

interface LabTalentCardProps {
  talent: LabTalent
}

function decodeHtmlEntities(text: string): string {
  const textarea = document.createElement('textarea')
  textarea.innerHTML = text
  return textarea.value
}

const LabTalentCard: React.FC<LabTalentCardProps> = ({ talent }) => {
  const navigate = useNavigate()
  const initials = talent.name.slice(0, 1)

  return (
    <Card
      hoverable
      size="small"
      onClick={() => navigate(`/lab/talents/${talent.talent_id}`)}
      style={{ borderRadius: 12, height: '100%' }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Space align="center">
          <Avatar
            size={48}
            src={undefined}
            style={{ background: dt.gradient, color: '#fff', fontWeight: 600 }}
          >
            {initials}
          </Avatar>
          <div>
            <Text strong style={{ fontSize: 16, display: 'block' }}>
              {talent.name}
            </Text>
            <Space size={4} wrap>
              <Tag>{ROLE_LABELS[talent.role_type] || talent.role_type}</Tag>
              {talent.academic_level && (
                <Tag color="blue">
                  {LEVEL_LABELS[talent.academic_level] || talent.academic_level}
                </Tag>
              )}
            </Space>
          </div>
        </Space>

        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
            {talent.parent_lab}
          </Text>
          {talent.lab_name && talent.lab_name !== talent.parent_lab && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
              {talent.lab_name}
            </Text>
          )}
          {talent.current_title && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
              {talent.current_title}
            </Text>
          )}
        </div>

        {talent.research_areas && talent.research_areas.length > 0 && (
          <Space size={4} wrap style={{ minHeight: 44 }}>
            {talent.research_areas.slice(0, 4).map(area => (
              <Tag key={area} color="geekblue" style={{ fontSize: 11, maxWidth: 160 }}>
                {decodeHtmlEntities(area)}
              </Tag>
            ))}
            {talent.research_areas.length > 4 && (
              <Tag style={{ fontSize: 11 }}>+{talent.research_areas.length - 4}</Tag>
            )}
          </Space>
        )}
      </Space>
    </Card>
  )
}

export default LabTalentCard

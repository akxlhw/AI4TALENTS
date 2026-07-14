import { Tag, Typography, Space, Avatar } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { LabTalent } from '../../../types'
import { ROLE_LABELS, ROLE_COLORS, LEVEL_LABELS } from '../constants/lab-role'

const { Text } = Typography

interface LabTalentCardProps {
  talent: LabTalent
}

const LabTalentCard: React.FC<LabTalentCardProps> = ({ talent }) => {
  const navigate = useNavigate()
  const initials = talent.name.slice(0, 1)
  const roleColor = ROLE_COLORS[talent.role_type] || ROLE_COLORS.unknown
  const roleLabel = ROLE_LABELS[talent.role_type] || ROLE_LABELS.unknown

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/lab/talents/${talent.talent_id}`)}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(`/lab/talents/${talent.talent_id}`)
        }
      }}
      style={{
        borderRadius: 14,
        background: '#fff',
        padding: 16,
        cursor: 'pointer',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        border: '1px solid #edf0f4',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-3px)'
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(13,43,78,0.10)'
        e.currentTarget.style.borderColor = roleColor
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = ''
        e.currentTarget.style.borderColor = '#edf0f4'
      }}
    >
      {/* Header: avatar + name + role */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <Avatar
            size={44}
            src={talent.photo_url || undefined}
            style={{
              background: `linear-gradient(135deg, ${roleColor}, ${roleColor}dd)`,
              color: '#fff',
              fontWeight: 600,
            }}
          >
            {initials}
          </Avatar>
          {/* Role indicator dot */}
          <div
            style={{
              position: 'absolute',
              bottom: -1,
              right: -1,
              width: 14,
              height: 14,
              borderRadius: '50%',
              border: '2.5px solid #fff',
              background: roleColor,
            }}
          />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text
            strong
            ellipsis
            style={{ fontSize: 15, display: 'block', lineHeight: 1.3 }}
          >
            {talent.name}
          </Text>
          <Space size={4} wrap style={{ marginTop: 2 }}>
            <Tag
              style={{
                fontSize: 11,
                margin: 0,
                padding: '0 8px',
                lineHeight: '20px',
                borderRadius: 10,
                border: 'none',
                background: `${roleColor}15`,
                color: roleColor,
                fontWeight: 500,
              }}
            >
              {roleLabel}
            </Tag>
            {talent.academic_level && (
              <Tag
                style={{
                  fontSize: 11,
                  margin: 0,
                  padding: '0 8px',
                  lineHeight: '20px',
                  borderRadius: 10,
                  border: 'none',
                  background: 'var(--domain-light-bg, #F0F9FF)',
                  color: 'var(--domain-secondary, #0EA5E9)',
                }}
              >
                {LEVEL_LABELS[talent.academic_level] || talent.academic_level}
              </Tag>
            )}
          </Space>
        </div>
      </div>

      {/* Affiliation */}
      <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
        {talent.lab_name && talent.lab_name !== talent.parent_lab ? (
          <>
            <div>{talent.lab_name}</div>
            <div style={{ fontSize: 11 }}>{talent.parent_lab}</div>
          </>
        ) : (
          <div>{talent.parent_lab}</div>
        )}
      </div>

      {/* Current title */}
      {talent.current_title && (
        <Text
          ellipsis
          style={{ fontSize: 12, color: '#64748b', display: 'block' }}
          title={talent.current_title}
        >
          {talent.current_title}
        </Text>
      )}

      {/* Research areas */}
      {talent.research_areas && talent.research_areas.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 'auto', paddingTop: 4 }}>
          {talent.research_areas.slice(0, 3).map(area => (
            <span
              key={area}
              style={{
                fontSize: 11,
                padding: '1px 8px',
                borderRadius: 8,
                background: '#f1f5f9',
                color: '#475569',
                maxWidth: 140,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={area}
            >
              {area}
            </span>
          ))}
          {talent.research_areas.length > 3 && (
            <span style={{ fontSize: 11, color: '#94a3b8', lineHeight: '20px' }}>
              +{talent.research_areas.length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default LabTalentCard

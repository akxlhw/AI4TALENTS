import { Avatar, Progress, Select, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { IndustryTalentSummary } from '../../../services/api/industry'
import { useUpdateCandidateStatus } from '../../../hooks/useIndustryQueries'
import { getErrorMessage } from '../../../utils'
import {
  CANDIDATE_STATUS_COLORS,
  CANDIDATE_STATUS_LABELS,
  CANDIDATE_STATUS_OPTIONS,
  formatScore,
  scoreColor,
} from '../constants/industry-config'

const { Text } = Typography

interface IndustryTalentCardProps {
  talent: IndustryTalentSummary
}

const IndustryTalentCard: React.FC<IndustryTalentCardProps> = ({ talent }) => {
  const navigate = useNavigate()
  const updateStatus = useUpdateCandidateStatus()

  const score = talent.best_match_score
  const color = scoreColor(score)
  // The primary position is the hit carrying the best match score
  const primary =
    talent.positions.reduce<(typeof talent.positions)[number] | null>(
      (best, p) =>
        best === null || (p.match_score ?? -1) > (best.match_score ?? -1) ? p : best,
      null
    ) ?? null
  const otherPositions = primary
    ? talent.positions.filter(p => p.position_id !== primary.position_id)
    : []
  const matchTags = primary?.match_tags ?? []
  const status = primary?.status || 'new'

  const goDetail = () => navigate(`/industry/talents/${talent.talent_id}`)

  const handleStatusChange = async (value: string) => {
    if (!primary) return
    try {
      await updateStatus.mutateAsync({
        talentId: talent.talent_id,
        positionId: primary.position_id,
        patch: { status: value },
      })
      message.success(`状态已更新为「${CANDIDATE_STATUS_LABELS[value] || value}」`)
    } catch (e) {
      message.error(getErrorMessage(e, '状态更新失败'))
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={goDetail}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          goDetail()
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
        e.currentTarget.style.boxShadow = '0 10px 28px rgba(107,70,193,0.12)'
        e.currentTarget.style.borderColor = 'var(--domain-secondary, #805AD5)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = ''
        e.currentTarget.style.borderColor = '#edf0f4'
      }}
    >
      {/* Header: avatar + identity | score ring (visual anchor) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Avatar
          size={48}
          src={talent.photo_url || undefined}
          style={{
            background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
            color: '#fff',
            fontWeight: 600,
            fontSize: 18,
            flexShrink: 0,
          }}
        >
          {talent.name.slice(0, 1)}
        </Avatar>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text strong ellipsis style={{ fontSize: 15, display: 'block', lineHeight: 1.3 }}>
            {talent.name}
          </Text>
          <Text
            ellipsis
            style={{ fontSize: 12, color: '#64748b', display: 'block', marginTop: 2 }}
            title={[talent.current_title, talent.current_org].filter(Boolean).join(' · ')}
          >
            {[talent.current_title, talent.current_org].filter(Boolean).join(' · ') || '—'}
          </Text>
        </div>
        {/* Score ring — colored by tier (80+ 绿 / 65-79 黄 / 其余灰) */}
        <div style={{ flexShrink: 0, textAlign: 'center' }}>
          <Progress
            type="circle"
            size={52}
            percent={score ?? 0}
            strokeColor={color}
            strokeWidth={7}
            trailColor="#f1f5f9"
            format={() => (
              <span style={{ fontSize: 17, fontWeight: 700, color, lineHeight: 1 }}>
                {formatScore(score)}
              </span>
            )}
          />
        </div>
      </div>

      {/* Meta line: degree · years · location */}
      <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5, minHeight: 18 }}>
        {[talent.degree, talent.years_of_exp, talent.location].filter(Boolean).join(' · ')}
      </div>

      {/* Match tags (neutral gray — data area stays neutral) */}
      {matchTags.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {matchTags.slice(0, 3).map(tag => (
            <span
              key={tag}
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
              title={tag}
            >
              {tag}
            </span>
          ))}
          {matchTags.length > 3 && (
            <span style={{ fontSize: 11, color: '#94a3b8', lineHeight: '20px' }}>
              +{matchTags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Matched positions (purple — the domain accent) */}
      {primary && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 'auto' }}>
          <Tag
            style={{
              fontSize: 11,
              margin: 0,
              padding: '0 8px',
              lineHeight: '20px',
              borderRadius: 10,
              border: 'none',
              background: 'var(--domain-light-bg, #FAF5FF)',
              color: 'var(--domain-badge-bg, #6B46C1)',
              fontWeight: 500,
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={primary.title}
          >
            {primary.title}
            {primary.match_score != null && ` · ${formatScore(primary.match_score)}`}
          </Tag>
          {otherPositions.slice(0, 1).map(p => (
            <Tag
              key={p.position_id}
              style={{
                fontSize: 11,
                margin: 0,
                padding: '0 8px',
                lineHeight: '20px',
                borderRadius: 10,
                border: '1px solid var(--domain-hover-bg, #F3E8FF)',
                background: '#fff',
                color: 'var(--domain-badge-bg, #6B46C1)',
                maxWidth: 140,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
              title={p.title}
            >
              {p.title}
            </Tag>
          ))}
          {talent.positions.length > 2 && (
            <span style={{ fontSize: 11, color: '#94a3b8', lineHeight: '20px' }}>
              +{talent.positions.length - 2}
            </span>
          )}
        </div>
      )}

      {/* Footer: status tag + quick status switch (no forced detour to detail) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: 8,
          borderTop: '1px solid #f4f6f9',
        }}
        onClick={e => e.stopPropagation()}
        onKeyDown={e => e.stopPropagation()}
      >
        <Tag
          color={CANDIDATE_STATUS_COLORS[status] || 'default'}
          style={{ margin: 0, fontSize: 11, borderRadius: 10, padding: '0 8px' }}
        >
          {CANDIDATE_STATUS_LABELS[status] || status}
        </Tag>
        {primary && (
          <Select
            size="small"
            variant="borderless"
            value={status}
            options={CANDIDATE_STATUS_OPTIONS}
            loading={updateStatus.isPending}
            onChange={handleStatusChange}
            style={{ width: 96, fontSize: 12 }}
            popupMatchSelectWidth={110}
            aria-label="修改候选人状态"
          />
        )}
      </div>
    </div>
  )
}

export default IndustryTalentCard

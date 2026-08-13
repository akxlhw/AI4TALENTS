import { Avatar, Card, Select, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { IndustryTalentSummary } from '../../../services/api/industry'
import { useUpdateCandidateStatus } from '../../../hooks/useIndustryQueries'
import { getErrorMessage } from '../../../utils'
import {
  CANDIDATE_STATUS_COLORS,
  CANDIDATE_STATUS_LABELS,
  CANDIDATE_STATUS_OPTIONS,
  formatScore,
  scoreBg,
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
  const primary = talent.positions.reduce<(typeof talent.positions)[number] | null>(
    (best, p) => best === null || (p.match_score ?? -1) > (best.match_score ?? -1) ? p : best, null
  ) ?? null
  const otherPositions = primary ? talent.positions.filter(p => p.position_id !== primary.position_id) : []
  const matchTags = primary?.match_tags ?? []
  const status = primary?.status || 'new'

  const goDetail = () => navigate(`/industry/talents/${talent.talent_id}`)

  const handleStatusChange = async (value: string) => {
    if (!primary) return
    try {
      await updateStatus.mutateAsync({
        talentId: talent.talent_id, positionId: primary.position_id, patch: { status: value },
      })
      message.success(`状态已更新为「${CANDIDATE_STATUS_LABELS[value] || value}」`)
    } catch (e) {
      message.error(getErrorMessage(e, '状态更新失败'))
    }
  }

  return (
    <Card
      className="domain-card"
      hoverable
      styles={{ body: { padding: '14px 16px' } }}
      style={{
        borderRadius: 12,
        borderLeft: `3px solid ${color}`,
        height: '100%',
        transition: 'all 0.2s ease',
        cursor: 'pointer',
      }}
      onClick={goDetail}
    >
      {/* Header: avatar + name (left) | score ring (right) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <Avatar
          size={36}
          src={talent.photo_url || undefined}
          style={{
            background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
            color: '#fff', fontWeight: 600, fontSize: 15, flexShrink: 0,
          }}
        >
          {talent.name.slice(0, 1)}
        </Avatar>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text strong ellipsis style={{ fontSize: 14, display: 'block' }}>
            {talent.name}
          </Text>
        </div>
        {/* Grade badge — replaces circle ring for discrete grade display */}
        <div
          style={{
            flexShrink: 0,
            width: 40,
            height: 40,
            borderRadius: 10,
            background: scoreBg(score),
            border: `2px solid ${color}30`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            lineHeight: 1,
          }}
        >
          <span style={{ fontSize: 16, fontWeight: 800, color }}>{formatScore(score)}</span>
        </div>
      </div>

      {/* Current position — 2-line clamp so long titles don't get hidden */}
      <div
        style={{
          fontSize: 12,
          color: 'var(--text-secondary)',
          marginBottom: 8,
          paddingLeft: 46, // align with avatar right edge
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          lineHeight: '18px',
          maxHeight: 36,
        }}
      >
        {talent.current_title && (
          <span style={{ fontWeight: 500, color: '#475569' }}>{talent.current_title}</span>
        )}
        {talent.current_title && talent.current_org && (
          <span style={{ color: '#94a3b8', margin: '0 3px' }}>·</span>
        )}
        {talent.current_org && <span>{talent.current_org}</span>}
        {!talent.current_title && !talent.current_org && <span>—</span>}
      </div>

      {/* Match tags */}
      {matchTags.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
          {matchTags.slice(0, 3).map(tag => (
            <Tag key={tag} color="purple" style={{ fontSize: 11, margin: 0, borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
              {tag}
            </Tag>
          ))}
        </div>
      )}

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
        <div>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>学历</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333' }}>{talent.degree || '-'}</div>
        </div>
        <div>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>年限</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333' }}>{talent.years_of_exp || '-'}</div>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>地区</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {talent.location || '-'}
          </div>
        </div>
      </div>

      {/* Footer: position tags (line 1) + status & action (line 2) */}
      <div
        style={{ paddingTop: 8, borderTop: '1px solid #f4f6f9' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Position tags row */}
        {(primary || otherPositions.length > 0) && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center', marginBottom: 6 }}>
            {primary && (
              <Tag style={{ fontSize: 11, margin: 0, padding: '0 6px', lineHeight: '18px', borderRadius: 4,
                background: 'var(--domain-light-bg, #FAF5FF)', color: 'var(--domain-badge-bg, #6B46C1)', border: 'none' }}
                title={primary.title}>
                {primary.title.length > 12 ? primary.title.slice(0, 12) + '…' : primary.title}
              </Tag>
            )}
            {otherPositions.length > 0 && (
              <Text type="secondary" style={{ fontSize: 11 }}>+{otherPositions.length}岗位</Text>
            )}
          </div>
        )}

        {/* Status + action row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Tag color={CANDIDATE_STATUS_COLORS[status] || 'default'} style={{ margin: 0, fontSize: 11, borderRadius: 10, padding: '0 8px' }}>
            {CANDIDATE_STATUS_LABELS[status] || status}
          </Tag>
          {primary && (
            <Select size="small" variant="borderless" value={status} options={CANDIDATE_STATUS_OPTIONS}
              loading={updateStatus.isPending} onChange={handleStatusChange}
              style={{ width: 86, fontSize: 12 }} popupMatchSelectWidth={110} aria-label="修改候选人状态" />
          )}
        </div>
      </div>
    </Card>
  )
}

export default IndustryTalentCard

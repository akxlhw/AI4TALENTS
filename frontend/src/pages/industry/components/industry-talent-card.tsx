import { Avatar, Card, Progress, Select, Space, Tag, Typography, message, Row, Col } from 'antd'
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
      {/* Header: avatar + identity | score ring */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <Space align="start">
          <Avatar
            size={40}
            src={talent.photo_url || undefined}
            style={{
              background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
              color: '#fff', fontWeight: 600, fontSize: 16, flexShrink: 0,
            }}
          >
            {talent.name.slice(0, 1)}
          </Avatar>
          <div>
            <Text strong style={{ fontSize: 14, display: 'block' }}>
              {talent.name}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
              {[talent.current_title, talent.current_org].filter(Boolean).join(' · ') || '—'}
            </Text>
          </div>
        </Space>
        <Progress
          type="circle" size={48} percent={score ?? 0} strokeColor={color} strokeWidth={7}
          trailColor="#f1f5f9"
          format={() => (
            <span style={{ fontSize: 15, fontWeight: 700, color, lineHeight: 1 }}>{formatScore(score)}</span>
          )}
        />
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
      <Row gutter={16} style={{ marginBottom: 8 }}>
        <Col span={8}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>学历</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333' }}>{talent.degree || '-'}</div>
        </Col>
        <Col span={8}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>年限</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333' }}>{talent.years_of_exp || '-'}</div>
        </Col>
        <Col span={8}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>地区</Text>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {talent.location || '-'}
          </div>
        </Col>
      </Row>

      {/* Footer: status + position tags */}
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid #f4f6f9' }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
          <Tag color={CANDIDATE_STATUS_COLORS[status] || 'default'} style={{ margin: 0, fontSize: 11, borderRadius: 10, padding: '0 8px' }}>
            {CANDIDATE_STATUS_LABELS[status] || status}
          </Tag>
          {primary && (
            <Tag style={{ fontSize: 11, margin: 0, padding: '0 6px', lineHeight: '18px', borderRadius: 4,
              background: 'var(--domain-light-bg, #FAF5FF)', color: 'var(--domain-badge-bg, #6B46C1)', border: 'none' }}
              title={primary.title}>
              {primary.title.length > 10 ? primary.title.slice(0, 10) + '…' : primary.title}
            </Tag>
          )}
          {otherPositions.length > 0 && (
            <Text type="secondary" style={{ fontSize: 11 }}>+{otherPositions.length}岗位</Text>
          )}
        </div>
        {primary && (
          <Select size="small" variant="borderless" value={status} options={CANDIDATE_STATUS_OPTIONS}
            loading={updateStatus.isPending} onChange={handleStatusChange}
            style={{ width: 90, fontSize: 12 }} popupMatchSelectWidth={110} aria-label="修改候选人状态" />
        )}
      </div>
    </Card>
  )
}

export default IndustryTalentCard

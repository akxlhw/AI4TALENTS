import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { TabsProps } from 'antd'
import {
  Avatar,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Divider,
  Input,
  Progress,
  Select,
  Space,
  Tabs,
  Tag,
  Timeline,
  Typography,
  message,
} from 'antd'
import { ArrowLeftOutlined, ExportOutlined } from '@ant-design/icons'
import { useIndustryTalent, useUpdateCandidateStatus } from '../../hooks/useIndustryQueries'
import { applyDomainCssVars } from '../../theme'
import { getErrorMessage } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import type {
  IndustryPositionMatchDetail,
  IndustryTalentDetail,
} from '../../services/api/industry'
import {
  CANDIDATE_STATUS_COLORS,
  CANDIDATE_STATUS_LABELS,
  CANDIDATE_STATUS_OPTIONS,
  SOURCE_PLATFORM_LABELS,
  formatScore,
  scoreColor,
} from './constants/industry-config'

const { Title, Text, Link } = Typography

const IndustryTalentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const talentId = id ? Number(id) : undefined
  const { data: talent, isLoading, error, refetch } = useIndustryTalent(talentId)

  useEffect(() => {
    applyDomainCssVars('industry')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="加载失败"
          description={getErrorMessage(error, '加载人才详情失败，请稍后重试')}
          action={{ label: '重试', onClick: () => refetch() }}
        />
      </div>
    )
  }

  if (!talent) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="人才不存在或已删除"
          description="该人才可能已被移除或链接有误"
          action={{ label: '返回行业人才库', onClick: () => navigate('/industry') }}
        />
      </div>
    )
  }

  const tabItems: TabsProps['items'] = [
    { key: 'info', label: '基本信息', children: <InfoTab talent={talent} /> },
    { key: 'timeline', label: '履历时间线', children: <TimelineTab talent={talent} /> },
    {
      key: 'positions',
      label: `岗位匹配${talent.positions.length > 0 ? ` (${talent.positions.length})` : ''}`,
      children: <PositionsTab talent={talent} />,
    },
  ]

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '16px 24px 48px' }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigateBack(navigate, '/industry')}
          style={{ color: 'var(--domain-primary, #1A365D)', fontWeight: 500, marginBottom: 4 }}
        >
          返回
        </Button>
        <BreadcrumbNav items={[{ label: '行业人才库', path: '/industry' }, { label: talent.name }]} />

        <TalentHeaderCard talent={talent} />

        <Card style={{ borderRadius: 12, marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
          <Tabs items={tabItems} defaultActiveKey="info" />
        </Card>
      </div>
    </div>
  )
}

// ---------- Header identity card ----------

const TalentHeaderCard: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => {
  const color = scoreColor(talent.best_match_score)
  return (
    <Card style={{ borderRadius: 14, border: 'none', boxShadow: '0 2px 12px rgba(26,54,93,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <Avatar
          size={72}
          src={talent.photo_url || undefined}
          style={{
            background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
            color: '#fff',
            fontWeight: 600,
            fontSize: 28,
            flexShrink: 0,
          }}
        >
          {talent.name.slice(0, 1)}
        </Avatar>

        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <Title level={3} style={{ margin: 0 }}>
              {talent.name}
            </Title>
            {talent.source && (
              <Tag
                style={{
                  margin: 0,
                  borderRadius: 10,
                  border: 'none',
                  background: '#f1f5f9',
                  color: '#475569',
                }}
              >
                {SOURCE_PLATFORM_LABELS[talent.source] || talent.source}
              </Tag>
            )}
          </div>
          <Text style={{ fontSize: 14, color: '#475569', display: 'block', marginTop: 6 }}>
            {[talent.current_title, talent.current_org].filter(Boolean).join(' · ') || '—'}
          </Text>
          <Text style={{ fontSize: 13, color: '#94a3b8', display: 'block', marginTop: 4 }}>
            {[talent.degree, talent.years_of_exp, talent.location].filter(Boolean).join(' · ')}
          </Text>
          {talent.expect && (
            <Text
              style={{ fontSize: 13, color: '#64748b', display: 'block', marginTop: 8 }}
              ellipsis={{ tooltip: talent.expect }}
            >
              求职意向:{talent.expect}
            </Text>
          )}
          {talent.profile_url && (
            <Link
              href={talent.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8 }}
            >
              <ExportOutlined />
              {talent.source === 'linkedin' ? 'LinkedIn 主页' : '脉脉主页'}
            </Link>
          )}
        </div>

        {/* Best match score ring */}
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <Progress
            type="circle"
            size={84}
            percent={talent.best_match_score ?? 0}
            strokeColor={color}
            strokeWidth={6}
            trailColor="#f1f5f9"
            format={() => (
              <div>
                <div style={{ fontSize: 24, fontWeight: 700, color, lineHeight: 1.1 }}>
                  {formatScore(talent.best_match_score)}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>最高匹配分</div>
              </div>
            )}
          />
        </div>
      </div>
    </Card>
  )
}

// ---------- Tab 1: basic info ----------

const InfoTab: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => (
  <Descriptions column={1} bordered size="small" labelStyle={{ width: 120 }}>
    <Descriptions.Item label="姓名">{talent.name}</Descriptions.Item>
    <Descriptions.Item label="现任公司">{talent.current_org || '—'}</Descriptions.Item>
    <Descriptions.Item label="现任头衔">{talent.current_title || '—'}</Descriptions.Item>
    <Descriptions.Item label="学历">{talent.degree || '—'}</Descriptions.Item>
    <Descriptions.Item label="工作年限">{talent.years_of_exp || '—'}</Descriptions.Item>
    <Descriptions.Item label="所在地">{talent.location || '—'}</Descriptions.Item>
    <Descriptions.Item label="求职意向">{talent.expect || '—'}</Descriptions.Item>
    <Descriptions.Item label="来源平台">
      {talent.source ? SOURCE_PLATFORM_LABELS[talent.source] || talent.source : '—'}
    </Descriptions.Item>
    <Descriptions.Item label="来源链接">
      {talent.profile_url ? (
        <Link href={talent.profile_url} target="_blank" rel="noopener noreferrer">
          {talent.profile_url}
        </Link>
      ) : (
        '—'
      )}
    </Descriptions.Item>
    <Descriptions.Item label="最近更新">
      {talent.updated_at ? talent.updated_at.slice(0, 10) : '—'}
    </Descriptions.Item>
  </Descriptions>
)

// ---------- Tab 2: experience timeline ----------

const TimelineTab: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => {
  const experiences = talent.experiences || []
  if (experiences.length === 0) {
    return <EmptyPlaceholder title="暂无履历数据" description="导入数据中没有该人才的履历信息" />
  }

  // Collect match tags across positions to pin onto matching experience segments
  const allTags = Array.from(new Set(talent.positions.flatMap(p => p.match_tags || [])))
  const tagsForOrg = (org?: string) => {
    if (!org) return [] as string[]
    return allTags.filter(tag => org.includes(tag) || tag.includes(org))
  }

  return (
    <div style={{ padding: '8px 4px' }}>
      <Timeline
        items={experiences.map((exp, i) => {
          const isCurrent = i === 0 || (exp.org && exp.org === talent.current_org)
          const orgTags = tagsForOrg(exp.org)
          return {
            color: isCurrent ? 'var(--domain-badge-bg, #6B46C1)' : '#cbd5e1',
            children: (
              <div style={{ paddingBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <Text strong style={{ fontSize: 14 }}>
                    {exp.org || '—'}
                  </Text>
                  {isCurrent && (
                    <Tag
                      style={{
                        margin: 0,
                        fontSize: 11,
                        borderRadius: 10,
                        border: 'none',
                        background: 'var(--domain-light-bg, #FAF5FF)',
                        color: 'var(--domain-badge-bg, #6B46C1)',
                      }}
                    >
                      现任
                    </Tag>
                  )}
                </div>
                {exp.title && (
                  <Text style={{ fontSize: 13, color: '#64748b', display: 'block', marginTop: 2 }}>
                    {exp.title}
                  </Text>
                )}
                <Text style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginTop: 2 }}>
                  {exp.range || exp.year || ''}
                </Text>
                {orgTags.length > 0 && (
                  <Space size={4} wrap style={{ marginTop: 6 }}>
                    {orgTags.map(tag => (
                      <span
                        key={tag}
                        style={{
                          fontSize: 11,
                          padding: '1px 8px',
                          borderRadius: 8,
                          background: '#f1f5f9',
                          color: '#475569',
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </Space>
                )}
              </div>
            ),
          }
        })}
      />
    </div>
  )
}

// ---------- Tab 3: position matches + recruiting state management ----------

const PositionsTab: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => {
  if (talent.positions.length === 0) {
    return (
      <EmptyPlaceholder
        title="暂未命中任何岗位"
        description="该人才还没有与岗位关联的匹配记录"
      />
    )
  }
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {talent.positions.map(p => (
        <PositionMatchCard key={p.position_id} talentId={talent.talent_id} match={p} />
      ))}
    </Space>
  )
}

const SUB_SCORES: { key: 'score_school' | 'score_company' | 'score_direction'; label: string }[] = [
  { key: 'score_school', label: '院校' },
  { key: 'score_company', label: '企业' },
  { key: 'score_direction', label: '方向' },
]

const PositionMatchCard: React.FC<{
  talentId: number
  match: IndustryPositionMatchDetail
}> = ({ talentId, match }) => {
  const updateStatus = useUpdateCandidateStatus()
  const [status, setStatus] = useState(match.status)
  const [touched, setTouched] = useState(match.touched)
  const [notes, setNotes] = useState(match.notes || '')
  const [saving, setSaving] = useState(false)

  const dirty =
    status !== match.status || touched !== match.touched || notes !== (match.notes || '')

  const hasSubScores = SUB_SCORES.some(s => match[s.key] !== null)
  const color = scoreColor(match.match_score)

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateStatus.mutateAsync({
        talentId,
        positionId: match.position_id,
        patch: { status, touched, notes },
      })
      message.success('已保存')
    } catch (e) {
      message.error(getErrorMessage(e, '保存失败'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card size="small" style={{ borderRadius: 12, border: '1px solid #edf0f4' }}>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {/* Left: position + scores */}
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Text strong style={{ fontSize: 15, color: 'var(--domain-badge-bg, #6B46C1)' }}>
              {match.title}
            </Text>
            <Tag
              color={CANDIDATE_STATUS_COLORS[match.status] || 'default'}
              style={{ margin: 0, borderRadius: 10 }}
            >
              {CANDIDATE_STATUS_LABELS[match.status] || match.status}
            </Tag>
          </div>

          {/* Total score bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
            <Text style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1, minWidth: 40 }}>
              {formatScore(match.match_score)}
            </Text>
            <Progress
              percent={match.match_score ?? 0}
              strokeColor={color}
              trailColor="#f1f5f9"
              showInfo={false}
              style={{ flex: 1, margin: 0 }}
            />
          </div>

          {/* Three-dimension sub scores (degrade to total-only when absent) */}
          {hasSubScores && (
            <div style={{ display: 'flex', gap: 20, marginTop: 10, flexWrap: 'wrap' }}>
              {SUB_SCORES.filter(s => match[s.key] !== null).map(s => (
                <div key={s.key} style={{ minWidth: 120, flex: 1 }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: 12,
                      color: '#94a3b8',
                      marginBottom: 2,
                    }}
                  >
                    <span>{s.label}</span>
                    <span style={{ color: '#475569', fontWeight: 500 }}>
                      {formatScore(match[s.key])}
                    </span>
                  </div>
                  <Progress
                    percent={match[s.key] ?? 0}
                    size="small"
                    strokeColor="#a3b3c9"
                    trailColor="#f1f5f9"
                    showInfo={false}
                    style={{ margin: 0 }}
                  />
                </div>
              ))}
            </div>
          )}

          {match.match_tags.length > 0 && (
            <Space size={4} wrap style={{ marginTop: 12 }}>
              {match.match_tags.map(tag => (
                <span
                  key={tag}
                  style={{
                    fontSize: 11,
                    padding: '1px 8px',
                    borderRadius: 8,
                    background: '#f1f5f9',
                    color: '#475569',
                  }}
                >
                  {tag}
                </span>
              ))}
            </Space>
          )}

          {match.match_reason && (
            <Text
              style={{ fontSize: 12, color: '#64748b', display: 'block', marginTop: 10, lineHeight: 1.6 }}
            >
              {match.match_reason}
            </Text>
          )}

          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 10 }}>
            {[
              match.source_platform &&
                (SOURCE_PLATFORM_LABELS[match.source_platform] || match.source_platform),
              match.batch && `批次 ${match.batch}`,
              match.updated_at && `更新于 ${match.updated_at.slice(0, 10)}`,
            ]
              .filter(Boolean)
              .join(' · ')}
          </Text>
        </div>

        <Divider type="vertical" style={{ height: 'auto', margin: '0 4px' }} />

        {/* Right: recruiting state editor */}
        <div style={{ width: 240, flexShrink: 0 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            招聘状态
          </Text>
          <Select
            style={{ width: '100%', marginTop: 6 }}
            value={status}
            options={CANDIDATE_STATUS_OPTIONS}
            onChange={setStatus}
          />
          <Checkbox
            checked={touched}
            onChange={e => setTouched(e.target.checked)}
            style={{ marginTop: 12 }}
          >
            已触达
          </Checkbox>
          <Input.TextArea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="招聘备注..."
            rows={3}
            style={{ marginTop: 12, fontSize: 12 }}
            maxLength={500}
          />
          <Button
            type="primary"
            size="small"
            block
            style={{ marginTop: 12 }}
            disabled={!dirty}
            loading={saving}
            onClick={handleSave}
          >
            保存
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default IndustryTalentDetailPage

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
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
  Typography,
  message,
} from 'antd'
import { ArrowLeftOutlined, DeleteOutlined, EditOutlined, ExportOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useIndustryTalent, useRemoveFromPosition, useUpdateCandidateStatus } from '../../hooks/useIndustryQueries'
import { applyDomainCssVars } from '../../theme'
import { getErrorMessage } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import '../../i18n/namespaces/industry'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import type {
  CandidateStatusPatch,
  IndustryPositionMatchDetail,
  IndustryTalentDetail,
} from '../../services/api/industry'
import {
  CANDIDATE_STATUS_COLORS,
  candidateStatusLabel,
  candidateStatusOptions,
  sourcePlatformLabel,
  badgeStyle,
  badgeWrap,
  formatScore,
  scoreColor,
} from './constants/industry-config'

const { Title, Text, Link } = Typography

const IndustryTalentDetailPage: React.FC = () => {
  const { t } = useTranslation(['industry', 'common'])
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
          title={t('industry:detail.loadFailed')}
          description={getErrorMessage(error, t('industry:detail.loadFailedDescription'))}
          action={{ label: t('common:actions.retry'), onClick: () => refetch() }}
        />
      </div>
    )
  }

  if (!talent) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title={t('industry:detail.notFoundTitle')}
          description={t('industry:detail.notFoundDescription')}
          action={{ label: t('industry:detail.backToLibrary'), onClick: () => navigate('/industry') }}
        />
      </div>
    )
  }

  const tabItems: TabsProps['items'] = [
    { key: 'info', label: t('industry:detail.tabs.info'), children: <InfoTab talent={talent} /> },
    { key: 'timeline', label: t('industry:detail.tabs.timeline'), children: <TimelineTab talent={talent} /> },
    {
      key: 'positions',
      label: `${t('industry:detail.tabs.positions')}${talent.positions.length > 0 ? ` (${talent.positions.length})` : ''}`,
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
          {t('industry:detail.back')}
        </Button>
        <BreadcrumbNav items={[{ label: t('industry:detail.breadcrumbRoot'), path: '/industry' }, { label: talent.name }]} />

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
  const { t } = useTranslation('industry')
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
                {sourcePlatformLabel(talent.source)}
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
              {t('detail.expect', { value: talent.expect })}
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
              {talent.source === 'linkedin'
                ? t('detail.profileLink.linkedin')
                : t('detail.profileLink.maimai')}
            </Link>
          )}
        </div>

        {/* Best match grade medal */}
        <div style={{ textAlign: 'center', ...badgeWrap(84) }}>
          <div style={badgeStyle(talent.best_match_score, 84)}>
            <span style={{ fontSize: 28 }}>
              {formatScore(talent.best_match_score)}
            </span>
            <span style={{ fontSize: 10, opacity: 0.85, marginTop: 2 }}>
              {talent.best_match_score != null
                ? t('detail.scoreValue', { score: Math.round(talent.best_match_score) })
                : ''}
            </span>
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{t('detail.bestMatch')}</div>
        </div>
      </div>
    </Card>
  )
}

// ---------- Tab 1: basic info ----------

const InfoTab: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => {
  const { t } = useTranslation('industry')
  return (
    <Descriptions column={1} bordered size="small" labelStyle={{ width: 120 }}>
      <Descriptions.Item label={t('detail.fields.name')}>{talent.name}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.currentOrg')}>{talent.current_org || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.currentTitle')}>{talent.current_title || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.degree')}>{talent.degree || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.yearsOfExp')}>{talent.years_of_exp || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.location')}>{talent.location || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.expect')}>{talent.expect || '—'}</Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.sourcePlatform')}>
        {talent.source ? sourcePlatformLabel(talent.source) : '—'}
      </Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.profileUrl')}>
        {talent.profile_url ? (
          <Link href={talent.profile_url} target="_blank" rel="noopener noreferrer">
            {talent.profile_url}
          </Link>
        ) : (
          '—'
        )}
      </Descriptions.Item>
      <Descriptions.Item label={t('detail.fields.updatedAt')}>
        {talent.updated_at ? talent.updated_at.slice(0, 10) : '—'}
      </Descriptions.Item>
    </Descriptions>
  )
}

// ---------- Tab 2: experience timeline ----------

const TimelineTab: React.FC<{ talent: IndustryTalentDetail }> = ({ talent }) => {
  const { t } = useTranslation('industry')
  const experiences = talent.experiences || []
  if (experiences.length === 0) {
    return (
      <EmptyPlaceholder
        title={t('detail.timelineEmpty.title')}
        description={t('detail.timelineEmpty.description')}
      />
    )
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
                      {t('detail.currentTag')}
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
  const { t } = useTranslation('industry')
  if (talent.positions.length === 0) {
    return (
      <EmptyPlaceholder
        title={t('detail.noPositionsTitle')}
        description={t('detail.noPositionsDescription')}
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

const SUB_SCORES: { key: 'score_school' | 'score_company' | 'score_direction'; labelKey: string }[] = [
  { key: 'score_school', labelKey: 'detail.subScores.school' },
  { key: 'score_company', labelKey: 'detail.subScores.company' },
  { key: 'score_direction', labelKey: 'detail.subScores.direction' },
]

const PositionMatchCard: React.FC<{
  talentId: number
  match: IndustryPositionMatchDetail
}> = ({ talentId, match }) => {
  const { t } = useTranslation(['industry', 'common'])
  const updateStatus = useUpdateCandidateStatus()
  const removeMutation = useRemoveFromPosition()
  const navigate = useNavigate()
  const [status, setStatus] = useState(match.status)
  const [touched, setTouched] = useState(match.touched)
  const [notes, setNotes] = useState(match.notes || '')
  const [matchScore, setMatchScore] = useState<number | null>(match.match_score)
  const [scoreSchool, setScoreSchool] = useState<number | null>(match.score_school)
  const [scoreCompany, setScoreCompany] = useState<number | null>(match.score_company)
  const [scoreDirection, setScoreDirection] = useState<number | null>(match.score_direction)
  const [saving, setSaving] = useState(false)

  const dirty =
    status !== match.status ||
    touched !== match.touched ||
    notes !== (match.notes || '')

  const color = scoreColor(matchScore ?? undefined)

  const handleSave = async () => {
    setSaving(true)
    try {
      // Build patch with only the dirty score fields + recruiting state
      const patch: Record<string, unknown> = { status, touched, notes }
      if (matchScore !== match.match_score) patch.match_score = matchScore
      if (scoreSchool !== match.score_school) patch.score_school = scoreSchool
      if (scoreCompany !== match.score_company) patch.score_company = scoreCompany
      if (scoreDirection !== match.score_direction) patch.score_direction = scoreDirection

      await updateStatus.mutateAsync({
        talentId,
        positionId: match.position_id,
        patch: patch as CandidateStatusPatch,
      })
      message.success(t('industry:detail.saved'))
    } catch (e) {
      message.error(getErrorMessage(e, t('industry:detail.saveFailed')))
    } finally {
      setSaving(false)
    }
  }

  const handleScoreChange = async (
    field: 'match_score' | 'score_school' | 'score_company' | 'score_direction',
    value: number | null
  ) => {
    try {
      await updateStatus.mutateAsync({
        talentId,
        positionId: match.position_id,
        patch: { [field]: value ?? 0 } as CandidateStatusPatch,
      })
      // No success toast — inline edit should be quiet
    } catch (e) {
      message.error(getErrorMessage(e, t('industry:detail.scoreUpdateFailed')))
      // Revert local state on failure
      if (field === 'match_score') setMatchScore(match.match_score)
      else if (field === 'score_school') setScoreSchool(match.score_school)
      else if (field === 'score_company') setScoreCompany(match.score_company)
      else if (field === 'score_direction') setScoreDirection(match.score_direction)
    }
  }

  const handleRemove = async () => {
    try {
      const result = await removeMutation.mutateAsync({
        talentId,
        positionId: match.position_id,
      })
      if (result.orphan_talent_deleted) {
        message.success(t('industry:detail.removeOrphanCleaned'))
        navigate('/industry')
      } else {
        message.success(t('industry:detail.removed'))
      }
    } catch (e) {
      message.error(getErrorMessage(e, t('industry:detail.removeFailed')))
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
              {candidateStatusLabel(match.status)}
            </Tag>
            <Text type="secondary" style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 2 }}>
              <EditOutlined style={{ fontSize: 10 }} />
              {t('industry:detail.scoresEditable')}
            </Text>
          </div>

          {/* Total score — grade medal + inline edit */}
          <Tooltip title={t('industry:detail.clickToEditScore')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12 }}>
              <div style={badgeWrap(44)}>
                <div style={badgeStyle(matchScore, 44)}>
                  <span style={{ fontSize: 16 }}>
                    {formatScore(matchScore)}
                  </span>
                </div>
              </div>
              <InputNumber
                value={matchScore ?? undefined}
                min={0}
                max={100}
                precision={1}
                size="small"
                style={{ width: 64, color: '#475569', borderRadius: 6 }}
                variant="filled"
                onChange={v => setMatchScore(v)}
                onBlur={() => matchScore !== match.match_score && handleScoreChange('match_score', matchScore)}
                onPressEnter={() => matchScore !== match.match_score && handleScoreChange('match_score', matchScore)}
              />
              <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#f1f5f9', overflow: 'hidden' }}>
                <div style={{ width: `${matchScore ?? 0}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s' }} />
              </div>
            </div>
          </Tooltip>

          {/* Three-dimension sub scores — editable (click number to edit) */}
          <div style={{ display: 'flex', gap: 20, marginTop: 10, flexWrap: 'wrap' }}>
            {SUB_SCORES.map(s => {
              const currentValue =
                s.key === 'score_school'
                  ? scoreSchool
                  : s.key === 'score_company'
                    ? scoreCompany
                    : scoreDirection
              const setter =
                s.key === 'score_school'
                  ? setScoreSchool
                  : s.key === 'score_company'
                    ? setScoreCompany
                    : setScoreDirection
              const original = match[s.key]
              return (
                <div key={s.key} style={{ minWidth: 120, flex: 1 }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: 12,
                      color: '#94a3b8',
                      marginBottom: 4,
                    }}
                  >
                    <span>{t(`industry:${s.labelKey}`)}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: scoreColor(currentValue),
                          minWidth: 16,
                        }}
                      >
                        {formatScore(currentValue)}
                      </span>
                      <InputNumber
                        value={currentValue ?? undefined}
                        min={0}
                        max={100}
                        precision={1}
                        size="small"
                        style={{ width: 48, fontSize: 12, color: '#475569', borderRadius: 4 }}
                        variant="filled"
                        onChange={v => setter(v)}
                        onBlur={() =>
                          currentValue !== original && handleScoreChange(s.key, currentValue)
                        }
                        onPressEnter={() =>
                          currentValue !== original && handleScoreChange(s.key, currentValue)
                        }
                      />
                    </div>
                  </div>
                  <div style={{ height: 4, borderRadius: 2, background: '#f1f5f9', overflow: 'hidden' }}>
                    <div style={{ width: `${currentValue ?? 0}%`, height: '100%', borderRadius: 2, background: scoreColor(currentValue), transition: 'width 0.3s' }} />
                  </div>
                </div>
              )
            })}
          </div>

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
              match.source_platform && sourcePlatformLabel(match.source_platform),
              match.batch && t('industry:detail.batch', { value: match.batch }),
              match.updated_at && t('industry:detail.updatedAt', { date: match.updated_at.slice(0, 10) }),
            ]
              .filter(Boolean)
              .join(' · ')}
          </Text>
        </div>

        <Divider type="vertical" style={{ height: 'auto', margin: '0 4px' }} />

        {/* Right: recruiting state editor */}
        <div style={{ width: 240, flexShrink: 0 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('industry:detail.recruitingStatus')}
          </Text>
          <Select
            style={{ width: '100%', marginTop: 6 }}
            value={status}
            options={candidateStatusOptions()}
            onChange={setStatus}
          />
          <Checkbox
            checked={touched}
            onChange={e => setTouched(e.target.checked)}
            style={{ marginTop: 12 }}
          >
            {t('industry:detail.touched')}
          </Checkbox>
          <Input.TextArea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder={t('industry:detail.notesPlaceholder')}
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
            {t('industry:detail.save')}
          </Button>
          <Popconfirm
            title={t('industry:detail.removeConfirmTitle')}
            description={t('industry:detail.removeConfirmDescription')}
            okText={t('industry:detail.remove')}
            cancelText={t('common:actions.cancel')}
            okButtonProps={{ danger: true }}
            onConfirm={handleRemove}
          >
            <Button
              danger
              size="small"
              block
              icon={<DeleteOutlined />}
              loading={removeMutation.isPending}
              style={{ marginTop: 8 }}
            >
              {t('industry:detail.removeButton')}
            </Button>
          </Popconfirm>
        </div>
      </div>
    </Card>
  )
}

export default IndustryTalentDetailPage

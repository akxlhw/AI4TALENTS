import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card,
  Input,
  Table,
  Typography,
  Tag,
  Space,
  Select,
  Empty,
  Spin,
  Button,
  message,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  BulbOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import AILoadingOverlay from '../../../components/AILoadingOverlay'
import '../../../i18n/namespaces/academic'
import type { TechDomain, JDFeatures, MatchResultItem } from '../../../types'

const { Text } = Typography
const { TextArea } = Input

interface School { school_id: number; school_name: string }
interface Country { country_code: string; country_name_cn: string }

interface JDMatchTabProps {
  schools: School[]
  countries: Country[]
  techDomains: TechDomain[]
  countryOptions: { value: string; label: string }[]
  schoolOptions: { value: number; label: string }[]
  techDomainOptions: { value: number; label: string }[]
  onAddToReference: (talentId: number, talentName: string) => void
}

const JD_STATE_KEY = 'jd_match_state'

const getSavedJDState = (): { jdText: string; parsedJdText: string; jdFeatures: JDFeatures | null; matchResults: MatchResultItem[]; jdTookMs: number | null } => {
  try {
    const saved = sessionStorage.getItem(JD_STATE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch { /* ignore */ }
  return { jdText: '', parsedJdText: '', jdFeatures: null, matchResults: [], jdTookMs: null }
}

const saveJDState = (text: string, parsedText: string, features: JDFeatures | null, results: MatchResultItem[], took: number | null) => {
  try {
    sessionStorage.setItem(JD_STATE_KEY, JSON.stringify({ jdText: text, parsedJdText: parsedText, jdFeatures: features, matchResults: results, jdTookMs: took }))
  } catch { /* ignore */ }
}

// Helper function to extract error message from API response
const getErrorMessage = (error: unknown, defaultMessage: string): string => {
  const err = error as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const firstError = detail[0] as { msg?: string }
    return firstError.msg || defaultMessage
  }
  return defaultMessage
}

const JDMatchTab: React.FC<JDMatchTabProps> = ({
  countryOptions,
  schoolOptions,
  techDomainOptions,
  onAddToReference,
}) => {
  const navigate = useNavigate()
  const { t } = useTranslation('academic')

  const savedJDState = getSavedJDState()
  const [jdText, setJdText] = useState(savedJDState.jdText)
  const [parsedJdText, setParsedJdText] = useState(savedJDState.parsedJdText)
  const [jdFeatures, setJdFeatures] = useState<JDFeatures | null>(savedJDState.jdFeatures)
  const [jdLoading, setJdLoading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [matchResults, setMatchResults] = useState<MatchResultItem[]>(savedJDState.matchResults)
  const [jdTookMs, setJdTookMs] = useState<number | null>(savedJDState.jdTookMs)
  const [jdPage, setJdPage] = useState(1)

  const [jdTechDomainFilter, setJdTechDomainFilter] = useState<number | undefined>()
  const [jdCountryFilter, setJdCountryFilter] = useState<string | undefined>()
  const [jdSchoolFilter, setJdSchoolFilter] = useState<number | undefined>()
  const [jdRoleFilter, setJdRoleFilter] = useState<string | undefined>()
  const [jdMinCitations, setJdMinCitations] = useState<number | undefined>()

  const handleParseJD = async () => {
    if (!jdText.trim()) {
      message.warning(t('jdMatch.enterJD'))
      return
    }
    setParsing(true)
    try {
      const response = await api.jdMatch.parse(jdText)
      const features = response.data
      setJdFeatures(features)
      setParsedJdText(jdText)
      saveJDState(jdText, jdText, features, matchResults, jdTookMs)
      message.success(t('jdMatch.parseSuccess'))
    } catch (error: unknown) {
      message.error(getErrorMessage(error, t('jdMatch.parseError')))
    } finally {
      setParsing(false)
    }
  }

  const handleMatch = async () => {
    if (!jdText.trim()) {
      message.warning(t('jdMatch.enterJD'))
      return
    }
    setJdLoading(true)
    try {
      const filters: Record<string, unknown> = {}
      if (jdTechDomainFilter) filters.tech_domain_id = jdTechDomainFilter
      if (jdCountryFilter) filters.country_code = jdCountryFilter
      if (jdSchoolFilter) filters.school_id = jdSchoolFilter
      if (jdRoleFilter) filters.role_type = jdRoleFilter
      if (jdMinCitations) filters.min_citations = jdMinCitations

      const response = await api.jdMatch.match({
        jd_text: jdText,
        config: {
          filters,
          limit: 50,
        },
      })
      const results = response.data.items || []
      const took = response.data.took_ms
      setMatchResults(results)
      setJdTookMs(took)

      setJdLoading(false)
      message.success(t('jdMatch.found', { n: response.data.total }))

      if (jdText !== parsedJdText) {
        try {
          const parseResponse = await api.jdMatch.parse(jdText)
          const features = parseResponse.data
          setJdFeatures(features)
          setParsedJdText(jdText)
          saveJDState(jdText, jdText, features, results, took)
        } catch {
          // 解析失败不影响匹配结果展示
        }
      } else {
        saveJDState(jdText, jdText, jdFeatures, results, took)
      }
    } catch (error: unknown) {
      message.error(getErrorMessage(error, t('jdMatch.matchError')))
      setJdLoading(false)
    }
  }

  const handleResetJD = () => {
    setJdText('')
    setParsedJdText('')
    setJdFeatures(null)
    setMatchResults([])
    setJdTookMs(null)
    setJdPage(1)
    setJdTechDomainFilter(undefined)
    setJdCountryFilter(undefined)
    setJdSchoolFilter(undefined)
    setJdRoleFilter(undefined)
    setJdMinCitations(undefined)
    sessionStorage.removeItem(JD_STATE_KEY)
  }

  const hasJdActiveFilters = jdTechDomainFilter || jdCountryFilter || jdSchoolFilter || jdRoleFilter || jdMinCitations

  const handleResetJdFilters = () => {
    setJdTechDomainFilter(undefined)
    setJdCountryFilter(undefined)
    setJdSchoolFilter(undefined)
    setJdRoleFilter(undefined)
    setJdMinCitations(undefined)
  }

  const jdColumns = [
    {
      title: t('columns.rank'),
      key: 'rank',
      width: 60,
      render: (_: unknown, __: MatchResultItem, index: number) => {
        const rank = (jdPage - 1) * 10 + index + 1
        return <Tag color={rank <= 3 ? 'gold' : 'default'}>{rank}</Tag>
      },
    },
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 100,
      render: (name: string, record: MatchResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    {
      title: t('columns.school'),
      key: 'school',
      width: 150,
      ellipsis: true,
      render: (_: unknown, record: MatchResultItem) => {
        if (record.education_school_name) {
          return (
            <span>
              {record.education_school_name}
              {record.company_school_name && record.company_school_name !== record.education_school_name && (
                <><br /><Text type="secondary" style={{ fontSize: 12 }}>{record.company_school_name}</Text></>
              )}
            </span>
          )
        }
        if (record.company_school_name) {
          return <span>{record.company_school_name}</span>
        }
        return <Text type="secondary">{record.school_name || '-'}</Text>
      },
    },
    {
      title: t('columns.recommendIndex'),
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 70,
      render: (score: number) => <Tag color={score >= 70 ? 'green' : score >= 50 ? 'blue' : 'default'}>{t('jdMatch.score', { n: score.toFixed(0) })}</Tag>,
      sorter: (a: MatchResultItem, b: MatchResultItem) => a.overall_score - b.overall_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: t('columns.matchReasons'),
      dataIndex: 'match_reasons',
      key: 'match_reasons',
      width: 200,
      render: (reasons: string[]) => (
        <Space size={[4, 4]} wrap>
          {reasons?.slice(0, 3).map((reason, idx) => <Tag key={idx} color="blue" style={{ margin: 0 }}>{reason}</Tag>)}
        </Space>
      ),
    },
    {
      title: t('columns.actions'),
      key: 'actions',
      width: 100,
      render: (_: unknown, record: MatchResultItem) => (
        <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => onAddToReference(record.talent_id, record.name)}>
          {t('searchTab.addToReference')}
        </Button>
      ),
    },
  ]

  return (
    <>
      <Card title={t('jdMatch.jdTitle')} style={{ marginBottom: 16 }}>
        <TextArea placeholder={t('jdMatch.placeholder')} value={jdText} onChange={(e) => setJdText(e.target.value)} rows={6} showCount maxLength={5000} />
        <Space style={{ marginTop: 12, flexWrap: 'wrap' }}>
          <Text type="secondary">{t('filters.label')}</Text>
          <Select placeholder={t('filters.techDomain')} value={jdTechDomainFilter} onChange={setJdTechDomainFilter} allowClear showSearch optionFilterProp="label" style={{ width: 140 }} options={techDomainOptions} />
          <Select placeholder={t('filters.country')} value={jdCountryFilter} onChange={setJdCountryFilter} allowClear showSearch optionFilterProp="label" style={{ width: 120 }} options={countryOptions} />
          <Select placeholder={t('filters.school')} value={jdSchoolFilter} onChange={setJdSchoolFilter} allowClear showSearch optionFilterProp="label" style={{ width: 180 }} options={schoolOptions} />
          <Select placeholder={t('filters.role')} value={jdRoleFilter} onChange={setJdRoleFilter} allowClear style={{ width: 140 }} options={[{ value: 'professor', label: t('roles.professor') }, { value: 'student', label: t('roles.student') }, { value: 'graduated', label: t('roles.graduate') }]} />
          <Select placeholder={t('filters.minCitations')} value={jdMinCitations} onChange={setJdMinCitations} allowClear style={{ width: 120 }} options={[{ value: 100, label: t('searchTab.minCitations.c100') }, { value: 500, label: t('searchTab.minCitations.c500') }, { value: 1000, label: t('searchTab.minCitations.c1000') }]} />
          {hasJdActiveFilters && <Button type="link" icon={<ReloadOutlined />} onClick={handleResetJdFilters}>{t('searchTab.resetFilters')}</Button>}
        </Space>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleMatch} loading={jdLoading}>{t('jdMatch.matchAction')} {jdTookMs && <Text type="secondary">({jdTookMs.toFixed(0)}ms)</Text>}</Button>
          <Button icon={<BulbOutlined />} onClick={handleParseJD} loading={parsing}>{t('jdMatch.parseAction')}</Button>
          <Button icon={<ReloadOutlined />} onClick={handleResetJD}>{t('jdMatch.reset')}</Button>
        </Space>
      </Card>
      {jdFeatures && (
        <Card title={t('jdMatch.parseResultTitle')} style={{ marginBottom: 16 }} size="small">
          <Space size={[4, 4]} wrap>
            {jdFeatures.research_areas?.length > 0 ? (
              jdFeatures.research_areas.map((area, idx) => <Tag key={idx} color="green">{area}</Tag>)
            ) : (
              <span style={{ color: '#999' }}>{t('jdMatch.noResearchAreas')}</span>
            )}
          </Space>
        </Card>
      )}
      <Card title={t('jdMatch.resultsTitle', { n: matchResults.length })}>
        <Spin spinning={jdLoading}>
          {matchResults.length > 0 ? (
            <Table
              dataSource={matchResults}
              columns={jdColumns}
              rowKey="talent_id"
              pagination={{ pageSize: 10, showTotal: (count) => t('jdMatch.candidatesTotal', { n: count }) }}
              scroll={{ x: 1200 }}
              onChange={(pagination) => setJdPage(pagination.current || 1)}
            />
          ) : (
            <Empty description={t('jdMatch.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>

      <AILoadingOverlay
        visible={jdLoading || parsing}
        title={parsing ? t('jdMatch.loadingParseTitle') : t('jdMatch.loadingMatchTitle')}
        steps={
          parsing
            ? [
                t('jdMatch.loadingSteps.connect'),
                t('jdMatch.loadingSteps.analyzeJD'),
                t('jdMatch.loadingSteps.extractSkills'),
                t('jdMatch.loadingSteps.identifyDirections'),
                t('jdMatch.loadingSteps.generateVectors'),
              ]
            : [
                t('jdMatch.loadingSteps.connect'),
                t('jdMatch.loadingSteps.parseInfo'),
                t('jdMatch.loadingSteps.searchCandidates'),
                t('jdMatch.loadingSteps.computeScores'),
                t('jdMatch.loadingSteps.generateReasons'),
                t('jdMatch.loadingSteps.rankResults'),
              ]
        }
      />
    </>
  )
}

export default JDMatchTab

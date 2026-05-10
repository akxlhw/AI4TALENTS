import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  BulbOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import AILoadingOverlay from '../../../components/AILoadingOverlay'
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
      message.warning('请输入职位描述')
      return
    }
    setParsing(true)
    try {
      const response = await api.jdMatch.parse(jdText)
      const features = response.data
      setJdFeatures(features)
      setParsedJdText(jdText)
      saveJDState(jdText, jdText, features, matchResults, jdTookMs)
      message.success('JD 解析成功')
    } catch (error: unknown) {
      message.error(getErrorMessage(error, 'JD 解析失败'))
    } finally {
      setParsing(false)
    }
  }

  const handleMatch = async () => {
    if (!jdText.trim()) {
      message.warning('请输入职位描述')
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
      message.success(`找到 ${response.data.total} 位匹配候选人`)

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
      message.error(getErrorMessage(error, '匹配失败，请检查 LLM 配置'))
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
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: MatchResultItem, index: number) => {
        const rank = (jdPage - 1) * 10 + index + 1
        return <Tag color={rank <= 3 ? 'gold' : 'default'}>{rank}</Tag>
      },
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      render: (name: string, record: MatchResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    {
      title: '院校机构',
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
      title: '推荐指数',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 70,
      render: (score: number) => <Tag color={score >= 70 ? 'green' : score >= 50 ? 'blue' : 'default'}>{score.toFixed(0)}分</Tag>,
      sorter: (a: MatchResultItem, b: MatchResultItem) => a.overall_score - b.overall_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '匹配原因',
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
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: MatchResultItem) => (
        <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => onAddToReference(record.talent_id, record.name)}>
          加入参考
        </Button>
      ),
    },
  ]

  return (
    <>
      <Card title="职位描述 (JD)" style={{ marginBottom: 16 }}>
        <TextArea placeholder="请粘贴职位描述内容，包括岗位职责、任职要求、技能要求等..." value={jdText} onChange={(e) => setJdText(e.target.value)} rows={6} showCount maxLength={5000} />
        <Space style={{ marginTop: 12, flexWrap: 'wrap' }}>
          <Text type="secondary">筛选:</Text>
          <Select placeholder="技术领域" value={jdTechDomainFilter} onChange={setJdTechDomainFilter} allowClear showSearch optionFilterProp="label" style={{ width: 140 }} options={techDomainOptions} />
          <Select placeholder="国家" value={jdCountryFilter} onChange={setJdCountryFilter} allowClear showSearch optionFilterProp="label" style={{ width: 120 }} options={countryOptions} />
          <Select placeholder="院校机构" value={jdSchoolFilter} onChange={setJdSchoolFilter} allowClear showSearch optionFilterProp="label" style={{ width: 180 }} options={schoolOptions} />
          <Select placeholder="角色" value={jdRoleFilter} onChange={setJdRoleFilter} allowClear style={{ width: 140 }} options={[{ value: 'professor', label: '教授/研究员' }, { value: 'student', label: '学生' }, { value: 'graduated', label: '毕业生' }]} />
          <Select placeholder="最少引用" value={jdMinCitations} onChange={setJdMinCitations} allowClear style={{ width: 120 }} options={[{ value: 100, label: '100次以上' }, { value: 500, label: '500次以上' }, { value: 1000, label: '1000次以上' }]} />
          {hasJdActiveFilters && <Button type="link" icon={<ReloadOutlined />} onClick={handleResetJdFilters}>重置筛选</Button>}
        </Space>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleMatch} loading={jdLoading}>智能匹配 {jdTookMs && <Text type="secondary">({jdTookMs.toFixed(0)}ms)</Text>}</Button>
          <Button icon={<BulbOutlined />} onClick={handleParseJD} loading={parsing}>解析 JD</Button>
          <Button icon={<ReloadOutlined />} onClick={handleResetJD}>重置</Button>
        </Space>
      </Card>
      {jdFeatures && (
        <Card title="JD 解析结果 - 研究方向" style={{ marginBottom: 16 }} size="small">
          <Space size={[4, 4]} wrap>
            {jdFeatures.research_areas?.length > 0 ? (
              jdFeatures.research_areas.map((area, idx) => <Tag key={idx} color="green">{area}</Tag>)
            ) : (
              <span style={{ color: '#999' }}>未识别到研究方向关键词</span>
            )}
          </Space>
        </Card>
      )}
      <Card title={`匹配结果 (${matchResults.length} 人)`}>
        <Spin spinning={jdLoading}>
          {matchResults.length > 0 ? (
            <Table
              dataSource={matchResults}
              columns={jdColumns}
              rowKey="talent_id"
              pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 位候选人` }}
              scroll={{ x: 1200 }}
              onChange={(pagination) => setJdPage(pagination.current || 1)}
            />
          ) : (
            <Empty description='请输入职位描述并点击"智能匹配"开始搜索' image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>

      <AILoadingOverlay
        visible={jdLoading || parsing}
        title={parsing ? '解析职位描述' : '智能匹配中'}
        steps={
          parsing
            ? ['连接 AI 服务', '分析职位描述', '提取技能要求', '识别研究方向', '生成特征向量']
            : ['连接 AI 服务', '解析关键信息', '搜索候选人', '计算匹配度', '生成推荐理由', '排序结果']
        }
      />
    </>
  )
}

export default JDMatchTab

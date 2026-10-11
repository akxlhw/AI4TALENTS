/**
 * 技术领域页面
 * 面向业务部门的主分析页面，从技术领域/技术方向看人才供给
 *
 * 页面逻辑：
 * 1. 页面初始化时加载用户权限范围内的总体统计数据
 * 2. 默认显示所有权限范围内的人才列表
 * 3. 用户可通过筛选区选择特定技术领域/方向来缩小范围
 *
 * v1.3: 使用 React Query 实现前端缓存
 */
import { useState, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card,
  Row,
  Col,
  Select,
  Input,
  Button,
  Table,
  Statistic,
  Empty,
  Spin,
  Tag,
  Space,
  Typography,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  TeamOutlined,
  AppstoreOutlined,
  UserOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import {
  useTechDomains,
  useTechDomainStats,
  useTechDomainTalents,
  useOverallTalents,
} from '../../hooks/useQueries'
import TopicTags from '../../components/TopicTags'
import '../../i18n/namespaces/academic'

const { Title, Text } = Typography

// 技术领域类型
interface TechDomain {
  tech_domain_id: number
  domain_code: string
  domain_name: string
  domain_name_en: string | null
  directions: TechDirection[]
}

// 技术方向类型
interface TechDirection {
  tech_direction_id: number
  direction_code: string
  direction_name: string
  tech_domain_id: number
}

// 人才明细数据类型
interface TalentItem {
  talent_id: number
  name: string
  name_en: string | null
  school_name: string | null
  role_type: string
  h_index: number
  works_count: number
  topic_tags: string[]
  openalex_topics: string[]  // OpenAlex研究主题（具体研究方向）
}

const TechDomainPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation(['academic', 'common'])
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [techDomainId, setTechDomainId] = useState<number | undefined>(
    searchParams.get('tech_domain_id') ? Number(searchParams.get('tech_domain_id')) : undefined
  )
  const [keyword, setKeyword] = useState('')
  const [countryId, setCountryId] = useState<number | undefined>()
  const [schoolId, setSchoolId] = useState<number | undefined>()
  const [roleType, setRoleType] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  // React Query hooks
  const { data: domainsData, isLoading: domainsLoading } = useTechDomains()
  const { data: statsData, isLoading: statsLoading } = useTechDomainStats(techDomainId)

  // Build talent query params
  const talentParams = useMemo(() => ({
    page,
    page_size: pageSize,
    country_code: countryId ? String(countryId) : undefined,
    school_id: schoolId,
    role_type: roleType,
    keyword: keyword || undefined,
  }), [page, pageSize, countryId, schoolId, roleType, keyword])

  // Use different hooks based on whether tech domain is selected
  const overallTalentsQuery = useOverallTalents(talentParams)
  const domainTalentsQuery = useTechDomainTalents(techDomainId!, talentParams)

  // Select the appropriate query result
  const talentsQuery = techDomainId ? domainTalentsQuery : overallTalentsQuery
  const { data: talentsData, isLoading: talentsLoading, refetch: refetchTalents } = talentsQuery

  // Extract data from query results
  const techDomains: TechDomain[] = domainsData?.items || []
  const stats = statsData || {
    talent_count: 0,
    professor_count: 0,
    student_count: 0,
    country_count: 0,
    school_count: 0,
  }
  const talentData: TalentItem[] = talentsData?.items || []
  const total = talentsData?.total || 0

  // 角色类型选项
  const roleTypeOptions = [
    { value: 'professor', label: t('roles.professor') },
    { value: 'student', label: t('roles.enrolledStudent') },
    { value: 'graduated', label: t('roles.graduated') },
    { value: 'unknown', label: t('roles.pendingConfirm') },
  ]

  // 技术领域选项
  const domainOptions = techDomains.map(d => ({
    value: d.tech_domain_id,
    label: d.domain_name,
  }))

  const handleTechDomainChange = (value: number | undefined) => {
    setTechDomainId(value)
    setPage(1)
  }

  const handleSearch = () => {
    setPage(1)
    refetchTalents()
  }

  const handleReset = () => {
    setTechDomainId(undefined)
    setKeyword('')
    setCountryId(undefined)
    setSchoolId(undefined)
    setRoleType(undefined)
    setPage(1)
  }

  const handleTableChange = (newPagination: TablePaginationConfig) => {
    setPage(newPagination.current || 1)
    setPageSize(newPagination.pageSize || 10)
  }

  // 人才明细表格列
  const talentColumns: ColumnsType<TalentItem> = [
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)}>{text}</a>
      ),
    },
    {
      title: t('columns.school'),
      dataIndex: 'school_name',
      key: 'school_name',
    },
    {
      title: t('columns.role'),
      dataIndex: 'role_type',
      key: 'role_type',
      render: (role) => {
        const roleMap: Record<string, { color: string; labelKey: string }> = {
          professor: { color: 'blue', labelKey: 'professor' },
          student: { color: 'green', labelKey: 'enrolledStudent' },
          graduated: { color: 'orange', labelKey: 'graduated' },
          unknown: { color: 'default', labelKey: 'pendingConfirm' },
        }
        const config = roleMap[role]
        return <Tag color={config?.color || 'default'}>{config ? t(`roles.${config.labelKey}`) : role}</Tag>
      },
    },
    {
      title: t('columns.hIndex'),
      dataIndex: 'h_index',
      key: 'h_index',
      sorter: true,
    },
    {
      title: t('columns.papersCount'),
      dataIndex: 'works_count',
      key: 'works_count',
      sorter: true,
    },
    {
      title: t('columns.researchDirections'),
      dataIndex: 'openalex_topics',
      key: 'openalex_topics',
      width: 200,
      render: (topics: string[], record) => {
        // 优先显示 openalex_topics，没有则回退到 topic_tags
        const displayTopics = topics && topics.length > 0 ? topics : record.topic_tags
        return <TopicTags tags={displayTopics} maxVisible={2} />
      },
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>{t('techDomain.title')}</Title>
        <Text type="secondary">{t('techDomain.subtitle')}</Text>
      </div>

      {/* 概要统计区 */}
      <Card style={{ marginBottom: 16 }}>
        <Spin spinning={statsLoading}>
          <Row gutter={24}>
            <Col span={4}>
              <Statistic
                title={t('stats.totalTalents')}
                value={stats.talent_count}
                prefix={<TeamOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title={t('stats.professors')}
                value={stats.professor_count}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title={t('stats.students')}
                value={stats.student_count}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title={t('stats.institutionsCovered')}
                value={stats.school_count}
                prefix={<AppstoreOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title={t('stats.countriesCovered')}
                value={stats.country_count}
                prefix={<AppstoreOutlined />}
              />
            </Col>
          </Row>
        </Spin>
      </Card>

      {/* 筛选区 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">{t('filters.techDomain')}</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder={t('techDomain.allOptional')}
              value={techDomainId}
              onChange={handleTechDomainChange}
              options={domainOptions}
              loading={domainsLoading}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">{t('filters.country')}</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder={t('techDomain.allOptional')}
              value={countryId}
              onChange={setCountryId}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">{t('filters.school')}</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder={t('techDomain.allOptional')}
              value={schoolId}
              onChange={setSchoolId}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">{t('filters.talentRole')}</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder={t('techDomain.allOptional')}
              value={roleType}
              onChange={setRoleType}
              options={roleTypeOptions}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">{t('filters.keyword')}</Text></div>
            <Input
              placeholder={t('techDomain.keywordPlaceholder')}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
            />
          </Col>
          <Col span={18}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">&nbsp;</Text></div>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                {t('techDomain.query')}
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                {t('techDomain.reset')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 人才列表 */}
      <Card>
        <Table
          columns={talentColumns}
          dataSource={talentData}
          rowKey="talent_id"
          loading={talentsLoading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => t('common:pagination.total', { n: count }),
          }}
          onChange={handleTableChange}
          locale={{
            emptyText: <Empty description={t('common:status.empty')} />,
          }}
        />
      </Card>
    </div>
  )
}

export default TechDomainPage

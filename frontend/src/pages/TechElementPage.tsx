/**
 * 技术要素页面 - MVP v1.1
 * 面向业务部门的主分析页面，从技术要素/技术方向看人才供给
 *
 * 页面逻辑：
 * 1. 页面初始化时加载用户权限范围内的总体统计数据
 * 2. 默认显示所有权限范围内的人才列表
 * 3. 用户可通过筛选区选择特定技术要素/方向来缩小范围
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
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
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import TopicTags from '../components/TopicTags'

const { Title, Text } = Typography

// 技术要素类型
interface TechElement {
  tech_element_id: number
  element_code: string
  element_name: string
  element_name_en: string | null
  directions: TechDirection[]
}

// 技术方向类型
interface TechDirection {
  tech_direction_id: number
  direction_code: string
  direction_name: string
  tech_element_id: number
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
  openalex_topics: string[]  // OpenAlex研究主题
}

// 总体统计类型
interface OverallStats {
  talent_count: number
  professor_count: number
  student_count: number
  country_count: number
  school_count: number
  tech_element_count: number
}

const TechElementPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [techElementId, setTechElementId] = useState<number | undefined>(
    searchParams.get('tech_element_id') ? Number(searchParams.get('tech_element_id')) : undefined
  )
  const [keyword, setKeyword] = useState('')
  const [countryId, setCountryId] = useState<number | undefined>()
  const [schoolId, setSchoolId] = useState<number | undefined>()
  const [roleType, setRoleType] = useState<string | undefined>()

  // 页面状态
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [elementsLoading, setElementsLoading] = useState(false)

  // 数据
  const [techElements, setTechElements] = useState<TechElement[]>([])
  const [overallStats, setOverallStats] = useState<OverallStats>({
    talent_count: 0,
    professor_count: 0,
    student_count: 0,
    country_count: 0,
    school_count: 0,
    tech_element_count: 0,
  })
  const [talentData, setTalentData] = useState<TalentItem[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  // 角色类型选项
  const roleTypeOptions = [
    { value: 'professor', label: '教授/研究员' },
    { value: 'student', label: '在读学生' },
    { value: 'graduated', label: '已毕业' },
    { value: 'unknown', label: '待确认' },
  ]

  // 获取技术要素列表
  const fetchTechElements = useCallback(async () => {
    setElementsLoading(true)
    try {
      const response = await api.techElements.list()
      setTechElements(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch tech elements:', error)
    } finally {
      setElementsLoading(false)
    }
  }, [])

  // 获取总体统计
  const fetchOverallStats = useCallback(async () => {
    setSummaryLoading(true)
    try {
      const response = await api.techElements.getOverallStats()
      setOverallStats(response.data)
    } catch (error) {
      console.error('Failed to fetch overall stats:', error)
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  // 获取总体人才列表
  const fetchOverallTalents = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      // 只传递有值的参数，避免传递 undefined 字符串
      const params: Record<string, any> = {
        page,
        page_size: pagination.pageSize,
      }
      if (countryId) params.country_id = countryId
      if (schoolId) params.school_id = schoolId
      if (roleType) params.role_type = roleType
      if (keyword) params.keyword = keyword

      const response = await api.techElements.getOverallTalents(params)
      setTalentData(response.data.items || [])
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pagination.pageSize,
        total: response.data.total || 0,
      })
    } catch (error) {
      console.error('Failed to fetch talents:', error)
    } finally {
      setLoading(false)
    }
  }, [countryId, schoolId, roleType, keyword, pagination.pageSize])

  // 获取筛选后的统计数据
  const fetchFilteredStats = useCallback(async () => {
    if (!techElementId) {
      fetchOverallStats()
      return
    }

    setSummaryLoading(true)
    try {
      const response = await api.techElements.getStats(techElementId)
      setOverallStats(prev => ({
        ...prev,
        talent_count: response.data.talent_count,
        country_count: response.data.country_count,
        school_count: response.data.school_count,
      }))
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setSummaryLoading(false)
    }
  }, [techElementId, fetchOverallStats])

  // 获取筛选后的人才列表
  const fetchFilteredTalents = useCallback(async (page = 1) => {
    if (!techElementId) {
      fetchOverallTalents(page)
      return
    }

    setLoading(true)
    try {
      // 只传递有值的参数
      const params: Record<string, any> = {
        page,
        page_size: pagination.pageSize,
      }
      if (countryId) params.country_id = countryId
      if (schoolId) params.school_id = schoolId
      if (roleType) params.role_type = roleType
      if (keyword) params.keyword = keyword

      const response = await api.techElements.getTalents(techElementId, params)
      setTalentData(response.data.items || [])
      setPagination({
        current: response.data.page || page,
        pageSize: response.data.page_size || pagination.pageSize,
        total: response.data.total || 0,
      })
    } catch (error) {
      console.error('Failed to fetch talents:', error)
    } finally {
      setLoading(false)
    }
  }, [techElementId, countryId, schoolId, roleType, keyword, pagination.pageSize, fetchOverallTalents])

  // 初始化加载
  useEffect(() => {
    fetchTechElements()
    fetchOverallStats()
  }, [])

  // 当筛选条件变化时重新加载数据
  useEffect(() => {
    // 初始化时加载人才列表
    fetchFilteredStats()
    fetchFilteredTalents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [techElementId])

  // 处理技术要素变化
  const handleTechElementChange = (value: number | undefined) => {
    setTechElementId(value)
    setPagination(prev => ({ ...prev, current: 1 }))
  }

  // 处理搜索
  const handleSearch = () => {
    setPagination(prev => ({ ...prev, current: 1 }))
    fetchFilteredStats()
    fetchFilteredTalents(1)
  }

  // 处理重置
  const handleReset = () => {
    setTechElementId(undefined)
    setKeyword('')
    setCountryId(undefined)
    setSchoolId(undefined)
    setRoleType(undefined)
    setPagination(prev => ({ ...prev, current: 1 }))
    fetchOverallStats()
    fetchOverallTalents()
  }

  // 处理表格分页变化
  const handleTableChange = (newPagination: any) => {
    const newPage = newPagination.current
    setPagination({
      ...pagination,
      current: newPage,
      pageSize: newPagination.pageSize,
    })
    fetchFilteredTalents(newPage)
  }

  // 技术要素选项
  const elementOptions = techElements.map(e => ({
    value: e.tech_element_id,
    label: e.element_name,
  }))

  // 人才明细表格列
  const talentColumns: ColumnsType<TalentItem> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)}>{text}</a>
      ),
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
    },
    {
      title: '角色',
      dataIndex: 'role_type',
      key: 'role_type',
      render: (role) => {
        const roleMap: Record<string, { color: string; text: string }> = {
          professor: { color: 'blue', text: '教授/研究员' },
          student: { color: 'green', text: '在读学生' },
          graduated: { color: 'orange', text: '已毕业' },
          unknown: { color: 'default', text: '待确认' },
        }
        const config = roleMap[role] || { color: 'default', text: role }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      sorter: true,
    },
    {
      title: '论文数',
      dataIndex: 'works_count',
      key: 'works_count',
      sorter: true,
    },
    {
      title: '研究方向',
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
    <div style={{ padding: 0 }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>技术要素</Title>
        <Text type="secondary">从技术要素/技术方向视角分析人才供给</Text>
      </div>

      {/* 概要统计区 */}
      <Card style={{ marginBottom: 16 }}>
        <Spin spinning={summaryLoading}>
          <Row gutter={24}>
            <Col span={4}>
              <Statistic
                title="人才总数"
                value={overallStats.talent_count}
                prefix={<TeamOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="教授/研究员"
                value={overallStats.professor_count}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="学生"
                value={overallStats.student_count}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="覆盖院校机构"
                value={overallStats.school_count}
                prefix={<AppstoreOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="覆盖国家"
                value={overallStats.country_count}
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
            <div style={{ marginBottom: 4 }}><Text type="secondary">技术要素</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="全部（可选筛选）"
              value={techElementId}
              onChange={handleTechElementChange}
              options={elementOptions}
              loading={elementsLoading}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="全部（可选筛选）"
              value={countryId}
              onChange={setCountryId}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">学校</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="全部（可选筛选）"
              value={schoolId}
              onChange={setSchoolId}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">人才角色</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="全部（可选筛选）"
              value={roleType}
              onChange={setRoleType}
              options={roleTypeOptions}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">关键词</Text></div>
            <Input
              placeholder="姓名/研究方向"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
            />
          </Col>
          <Col span={18}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">&nbsp;</Text></div>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
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
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
          locale={{
            emptyText: <Empty description="暂无数据" />,
          }}
        />
      </Card>
    </div>
  )
}

export default TechElementPage

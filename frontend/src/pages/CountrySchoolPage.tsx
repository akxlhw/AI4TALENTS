/**
 * 国家院校页面 - MVP v1.1
 * 面向平台部门的主分析页面，从区域/国家/学校看人才覆盖
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
  Tabs,
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
  BankOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'

const { Title, Text } = Typography

// 国家数据类型
interface Country {
  country_id: number
  country_code: string
  country_name_cn: string
  school_count: number
  professor_count: number
}

// 学校数据类型
interface School {
  school_id: number
  school_name: string
  country_name: string | null
  country_code: string | null
  professor_count: number
  student_count: number
}

// 技术要素数据类型
interface TechElement {
  tech_element_id: number
  element_code: string
  element_name: string
  directions: TechDirection[]
}

// 技术方向数据类型
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
}

const CountrySchoolPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [countryId, setCountryId] = useState<number | undefined>(
    searchParams.get('country_id') ? Number(searchParams.get('country_id')) : undefined
  )
  const [schoolId, setSchoolId] = useState<number | undefined>()
  const [techElementId, setTechElementId] = useState<number | undefined>()
  const [techDirectionId, setTechDirectionId] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [roleType, setRoleType] = useState<string | undefined>()

  // 页面状态
  const [activeTab, setActiveTab] = useState('school')
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)

  // 数据
  const [countries, setCountries] = useState<Country[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [techElements, setTechElements] = useState<TechElement[]>([])
  const [summary, setSummary] = useState({
    talentCount: 0,
    professorCount: 0,
    studentCount: 0,
    schoolCount: 0,
    techElementCount: 0,
  })
  const [talentData, setTalentData] = useState<TalentItem[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  // 角色类型选项
  const roleTypeOptions = [
    { value: 'professor', label: '教授/科研人员' },
    { value: 'student', label: '在读学生' },
    { value: 'graduated', label: '已毕业' },
    { value: 'unknown', label: '待确认' },
  ]

  // 加载国家列表
  const fetchCountries = useCallback(async () => {
    try {
      const response = await api.countries.list()
      setCountries(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch countries:', error)
    }
  }, [])

  // 加载学校列表
  const fetchSchools = useCallback(async () => {
    try {
      const response = await api.schools.list({ country_id: countryId })
      setSchools(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch schools:', error)
    }
  }, [countryId])

  // 加载技术要素列表
  const fetchTechElements = useCallback(async () => {
    try {
      const response = await api.techElements.list()
      setTechElements(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch tech elements:', error)
    }
  }, [])

  // 加载统计数据
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true)
    try {
      // 获取概览数据
      const overviewRes = await api.overview.get()
      const techSummaryRes = await api.techElements.getSummary()

      setSummary({
        talentCount: overviewRes.data.stats.talent_count,
        professorCount: overviewRes.data.stats.professor_count,
        studentCount: overviewRes.data.stats.student_count,
        schoolCount: overviewRes.data.stats.school_count,
        techElementCount: techSummaryRes.data.element_count,
      })
    } catch (error) {
      console.error('Failed to fetch summary:', error)
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  // 加载人才列表
  const fetchTalents = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const response = await api.talents.list({
        country_id: countryId,
        school_id: schoolId,
        role_type: roleType,
        keyword: keyword || undefined,
        page,
        page_size: pagination.pageSize,
      })
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

  // 初始化加载
  useEffect(() => {
    fetchCountries()
    fetchTechElements()
    fetchSummary()
    fetchSchools()
  }, [fetchCountries, fetchTechElements, fetchSummary, fetchSchools])

  // 当国家变化时重新加载学校
  useEffect(() => {
    fetchSchools()
  }, [countryId, fetchSchools])

  // 处理技术要素点击 - 跳转到技术要素页
  const handleTechElementClick = (elementId: number) => {
    navigate(`/tech-element?tech_element_id=${elementId}${countryId ? `&country_id=${countryId}` : ''}`)
  }

  // 处理搜索
  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 })
    fetchTalents(1)
  }

  // 处理重置
  const handleReset = () => {
    setCountryId(undefined)
    setSchoolId(undefined)
    setTechElementId(undefined)
    setTechDirectionId(undefined)
    setKeyword('')
    setRoleType(undefined)
    setTalentData([])
    setPagination({ ...pagination, total: 0 })
  }

  // 处理表格分页变化
  const handleTableChange = (newPagination: any) => {
    const newPage = newPagination.current
    setPagination({
      ...pagination,
      current: newPage,
      pageSize: newPagination.pageSize,
    })
    fetchTalents(newPage)
  }

  // 国家选项
  const countryOptions = countries.map(c => ({
    value: c.country_id,
    label: c.country_name_cn,
  }))

  // 学校选项
  const schoolOptions = schools.map(s => ({
    value: s.school_id,
    label: s.school_name,
  }))

  // 技术要素选项
  const techElementOptions = techElements.map(e => ({
    value: e.tech_element_id,
    label: e.element_name,
  }))

  // 当前选中的技术要素的方向选项
  const currentElement = techElements.find(e => e.tech_element_id === techElementId)
  const directionOptions = (currentElement?.directions || []).map(d => ({
    value: d.tech_direction_id,
    label: d.direction_name,
  }))

  // 学校表格列
  const schoolColumns: ColumnsType<School> = [
    {
      title: '院校',
      dataIndex: 'school_name',
      key: 'school_name',
      render: (text, record) => (
        <a onClick={() => navigate(`/schools/${record.school_id}`)}>{text}</a>
      ),
    },
    {
      title: '国家',
      dataIndex: 'country_name',
      key: 'country_name',
    },
    {
      title: '教授/科研人员',
      dataIndex: 'professor_count',
      key: 'professor_count',
    },
    {
      title: '学生',
      dataIndex: 'student_count',
      key: 'student_count',
    },
  ]

  // 技术要素分布表格列
  const techElementColumns: ColumnsType<TechElement> = [
    {
      title: '技术要素',
      dataIndex: 'element_name',
      key: 'element_name',
      render: (text, record) => (
        <a onClick={() => handleTechElementClick(record.tech_element_id)}>{text}</a>
      ),
    },
    {
      title: '技术方向数',
      key: 'direction_count',
      render: (_, record) => record.directions?.length || 0,
    },
  ]

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
          professor: { color: 'blue', text: '教授/科研人员' },
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
      title: '技术方向',
      dataIndex: 'topic_tags',
      key: 'topic_tags',
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {(tags || []).slice(0, 3).map((tag, index) => (
            <Tag key={index} style={{ marginBottom: 2 }}>{tag}</Tag>
          ))}
          {tags && tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>国家院校</Title>
        <Text type="secondary">从区域/国家/院校视角分析人才覆盖与技术要素分布</Text>
      </div>

      {/* 筛选区 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择国家"
              value={countryId}
              onChange={setCountryId}
              options={countryOptions}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">学校</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择学校"
              value={schoolId}
              onChange={setSchoolId}
              options={schoolOptions}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">技术要素</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择技术要素"
              value={techElementId}
              onChange={setTechElementId}
              options={techElementOptions}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">技术方向</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择技术方向"
              value={techDirectionId}
              onChange={setTechDirectionId}
              options={directionOptions}
              disabled={!techElementId}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">人才角色</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择角色"
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
          <Col span={12}>
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

      {/* 概要统计区 */}
      <Card style={{ marginBottom: 16 }}>
        <Spin spinning={summaryLoading}>
          <Row gutter={24}>
            <Col span={4}>
              <Statistic
                title="人才总数"
                value={summary.talentCount}
                prefix={<TeamOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="教授/科研人员"
                value={summary.professorCount}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="学生"
                value={summary.studentCount}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="覆盖院校"
                value={summary.schoolCount}
                prefix={<BankOutlined />}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="技术要素"
                value={summary.techElementCount}
                prefix={<AppstoreOutlined />}
              />
            </Col>
          </Row>
        </Spin>
      </Card>

      {/* Tabs 主视图区 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab="院校分布" key="school">
            <Table
              columns={schoolColumns}
              dataSource={schools}
              rowKey="school_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              locale={{
                emptyText: countryId ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="全部院校列表" />
                ),
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="技术要素分布" key="tech-element">
            <Table
              columns={techElementColumns}
              dataSource={techElements}
              rowKey="tech_element_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              locale={{
                emptyText: <Empty description="暂无技术要素数据" />,
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="人才明细" key="talent">
            <Table
              columns={talentColumns}
              dataSource={talentData}
              rowKey="talent_id"
              loading={loading}
              pagination={pagination}
              onChange={handleTableChange}
              locale={{
                emptyText: countryId || schoolId ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择国家或学校后查询" />
                ),
              }}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default CountrySchoolPage

/**
 * 技术要素页面 - MVP v1.1
 * 面向业务部门的主分析页面，从技术要素/技术方向看人才供给
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
  GlobalOutlined,
  BankOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'

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

// 国家分布数据类型
interface CountryDistribution {
  country_id: number
  country_name: string
  country_code: string | null
  talent_count: number
}

// 院校分布数据类型
interface SchoolDistribution {
  school_id: number
  school_name: string
  country_name: string | null
  talent_count: number
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

const TechElementPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [techElementId, setTechElementId] = useState<number | undefined>(
    searchParams.get('tech_element_id') ? Number(searchParams.get('tech_element_id')) : undefined
  )
  const [techDirectionId, setTechDirectionId] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [countryId, setCountryId] = useState<number | undefined>()
  const [schoolId, setSchoolId] = useState<number | undefined>()
  const [roleType, setRoleType] = useState<string | undefined>()

  // 页面状态
  const [activeTab, setActiveTab] = useState('country')
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [elementsLoading, setElementsLoading] = useState(false)

  // 数据
  const [techElements, setTechElements] = useState<TechElement[]>([])
  const [summary, setSummary] = useState({
    talentCount: 0,
    directionCount: 0,
    schoolCount: 0,
    countryCount: 0,
  })
  const [countryData, setCountryData] = useState<CountryDistribution[]>([])
  const [schoolData, setSchoolData] = useState<SchoolDistribution[]>([])
  const [talentData, setTalentData] = useState<TalentItem[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  // 角色类型选项
  const roleTypeOptions = [
    { value: 'professor', label: '教授/科研人员' },
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

  // 获取统计数据
  const fetchStats = useCallback(async () => {
    if (!techElementId) {
      setSummary({ talentCount: 0, directionCount: 0, schoolCount: 0, countryCount: 0 })
      return
    }

    setSummaryLoading(true)
    try {
      const response = await api.techElements.getStats(techElementId)
      setSummary({
        talentCount: response.data.talent_count,
        directionCount: response.data.direction_count,
        schoolCount: response.data.school_count,
        countryCount: response.data.country_count,
      })
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setSummaryLoading(false)
    }
  }, [techElementId])

  // 获取国家分布
  const fetchCountryDistribution = useCallback(async () => {
    if (!techElementId) {
      setCountryData([])
      return
    }

    setLoading(true)
    try {
      const response = await api.techElements.getCountries(techElementId, techDirectionId)
      setCountryData(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch country distribution:', error)
    } finally {
      setLoading(false)
    }
  }, [techElementId, techDirectionId])

  // 获取院校分布
  const fetchSchoolDistribution = useCallback(async (page = 1) => {
    if (!techElementId) {
      setSchoolData([])
      return
    }

    setLoading(true)
    try {
      const response = await api.techElements.getSchools(techElementId, {
        direction_id: techDirectionId,
        country_id: countryId,
        page,
        page_size: 10,
      })
      setSchoolData(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch school distribution:', error)
    } finally {
      setLoading(false)
    }
  }, [techElementId, techDirectionId, countryId])

  // 获取人才列表
  const fetchTalents = useCallback(async (page = 1) => {
    if (!techElementId) {
      setTalentData([])
      setPagination({ ...pagination, total: 0 })
      return
    }

    setLoading(true)
    try {
      const response = await api.techElements.getTalents(techElementId, {
        direction_id: techDirectionId,
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
  }, [techElementId, techDirectionId, countryId, schoolId, roleType, keyword, pagination.pageSize])

  // 初始化加载技术要素列表
  useEffect(() => {
    fetchTechElements()
  }, [fetchTechElements])

  // 当技术要素变化时加载数据
  useEffect(() => {
    if (techElementId) {
      fetchStats()
      fetchCountryDistribution()
      fetchSchoolDistribution()
      fetchTalents()
    }
  }, [techElementId, techDirectionId, fetchStats, fetchCountryDistribution, fetchSchoolDistribution, fetchTalents])

  // 处理技术要素变化
  const handleTechElementChange = (value: number | undefined) => {
    setTechElementId(value)
    setTechDirectionId(undefined)
  }

  // 处理国家点击 - 跳转到国家院校页
  const handleCountryClick = (countryId: number) => {
    navigate(`/country-school?country_id=${countryId}${techElementId ? `&tech_element_id=${techElementId}` : ''}`)
  }

  // 处理搜索
  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 })
    if (techElementId) {
      fetchStats()
      fetchCountryDistribution()
      fetchSchoolDistribution()
      fetchTalents(1)
    }
  }

  // 处理重置
  const handleReset = () => {
    setTechElementId(undefined)
    setTechDirectionId(undefined)
    setKeyword('')
    setCountryId(undefined)
    setSchoolId(undefined)
    setRoleType(undefined)
    setCountryData([])
    setSchoolData([])
    setTalentData([])
    setSummary({ talentCount: 0, directionCount: 0, schoolCount: 0, countryCount: 0 })
  }

  // 处理表格分页变化
  const handleTableChange = (newPagination: any) => {
    const newPage = newPagination.current
    setPagination({
      ...pagination,
      current: newPage,
      pageSize: newPagination.pageSize,
    })

    if (activeTab === 'school') {
      fetchSchoolDistribution(newPage)
    } else if (activeTab === 'talent') {
      fetchTalents(newPage)
    }
  }

  // 获取当前选中的技术要素的方向选项
  const currentElement = techElements.find(e => e.tech_element_id === techElementId)
  const directionOptions = (currentElement?.directions || []).map(d => ({
    value: d.tech_direction_id,
    label: d.direction_name,
  }))

  // 技术要素选项
  const elementOptions = techElements.map(e => ({
    value: e.tech_element_id,
    label: e.element_name,
  }))

  // 国家分布表格列
  const countryColumns: ColumnsType<CountryDistribution> = [
    {
      title: '国家',
      dataIndex: 'country_name',
      key: 'country_name',
      render: (text, record) => (
        <a onClick={() => handleCountryClick(record.country_id)}>{text}</a>
      ),
    },
    {
      title: '人才总数',
      dataIndex: 'talent_count',
      key: 'talent_count',
      sorter: true,
    },
  ]

  // 院校分布表格列
  const schoolColumns: ColumnsType<SchoolDistribution> = [
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
      title: '人才总数',
      dataIndex: 'talent_count',
      key: 'talent_count',
      sorter: true,
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
        <Title level={4} style={{ margin: 0 }}>技术要素</Title>
        <Text type="secondary">从技术要素/技术方向视角分析人才供给</Text>
      </div>

      {/* 筛选区 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">技术要素</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择技术要素"
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
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择国家"
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
              placeholder="选择学校"
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
                title="技术方向"
                value={summary.directionCount}
                prefix={<AppstoreOutlined />}
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
                title="覆盖国家"
                value={summary.countryCount}
                prefix={<GlobalOutlined />}
              />
            </Col>
          </Row>
        </Spin>
      </Card>

      {/* Tabs 主视图区 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab="国家分布" key="country">
            <Table
              columns={countryColumns}
              dataSource={countryData}
              rowKey="country_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: techElementId ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
                ),
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="院校分布" key="school">
            <Table
              columns={schoolColumns}
              dataSource={schoolData}
              rowKey="school_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: techElementId ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
                ),
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
                emptyText: techElementId ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
                ),
              }}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default TechElementPage

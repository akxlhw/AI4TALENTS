/**
 * 国家院校页面 - MVP v1.1
 * 面向平台部门的主分析页面，从区域/国家/学校看人才覆盖
 */
import { useState, useEffect } from 'react'
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

const { Title, Text } = Typography
const { TabPane } = Tabs

// 院校分布数据类型
interface SchoolDistribution {
  school_id: number
  school_name: string
  country_name: string
  talent_count: number
  professor_count: number
  student_count: number
}

// 技术要素分布数据类型
interface TechElementDistribution {
  tech_element_id: number
  tech_element_name: string
  tech_direction: string
  talent_count: number
  professor_count: number
  student_count: number
}

// 人才明细数据类型
interface TalentItem {
  talent_id: number
  name: string
  school_name: string
  role_type: string
  h_index: number
  works_count: number
  topic_tags: string[]
}

const CountrySchoolPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [region, setRegion] = useState<string | undefined>()
  const [country, setCountry] = useState<string | undefined>(
    searchParams.get('country_id') || undefined
  )
  const [school, setSchool] = useState<string | undefined>()
  const [techElement, setTechElement] = useState<string | undefined>(
    searchParams.get('tech_element') || undefined
  )
  const [techDirection, setTechDirection] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [roleType, setRoleType] = useState<string | undefined>()

  // 页面状态
  const [activeTab, setActiveTab] = useState('school')
  const [loading] = useState(false)
  const [summaryLoading] = useState(false)

  // 数据
  const [summary] = useState({
    talentCount: 0,
    professorCount: 0,
    studentCount: 0,
    schoolCount: 0,
    techElementCount: 0,
  })
  const [schoolData] = useState<SchoolDistribution[]>([])
  const [techElementData] = useState<TechElementDistribution[]>([])
  const [talentData] = useState<TalentItem[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  // 模拟区域选项
  const regionOptions = [
    { value: 'asia', label: '亚洲' },
    { value: 'europe', label: '欧洲' },
    { value: 'north_america', label: '北美洲' },
    { value: 'oceania', label: '大洋洲' },
  ]

  // 模拟国家选项 - 根据区域动态加载
  const countryOptions: Record<string, { value: string; label: string }[]> = {
    asia: [
      { value: 'cn', label: '中国' },
      { value: 'jp', label: '日本' },
      { value: 'sg', label: '新加坡' },
      { value: 'kr', label: '韩国' },
    ],
    europe: [
      { value: 'gb', label: '英国' },
      { value: 'de', label: '德国' },
      { value: 'fr', label: '法国' },
      { value: 'ch', label: '瑞士' },
    ],
    north_america: [
      { value: 'us', label: '美国' },
      { value: 'ca', label: '加拿大' },
    ],
    oceania: [
      { value: 'au', label: '澳大利亚' },
      { value: 'nz', label: '新西兰' },
    ],
  }

  // 模拟技术要素选项
  const techElementOptions = [
    { value: 'ai', label: '人工智能' },
    { value: 'ml', label: '机器学习' },
    { value: 'nlp', label: '自然语言处理' },
    { value: 'cv', label: '计算机视觉' },
    { value: 'robotics', label: '机器人' },
  ]

  const roleTypeOptions = [
    { value: 'professor', label: '教授/科研人员' },
    { value: 'student', label: '在读学生' },
    { value: 'graduated', label: '已毕业' },
    { value: 'unknown', label: '待确认' },
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
  const techElementColumns: ColumnsType<TechElementDistribution> = [
    {
      title: '技术要素',
      dataIndex: 'tech_element_name',
      key: 'tech_element_name',
      render: (text, record) => (
        <a onClick={() => handleTechElementClick(record.tech_element_id)}>{text}</a>
      ),
    },
    {
      title: '技术方向',
      dataIndex: 'tech_direction',
      key: 'tech_direction',
    },
    {
      title: '人才总数',
      dataIndex: 'talent_count',
      key: 'talent_count',
      sorter: true,
    },
    {
      title: '教授/科研人员',
      dataIndex: 'professor_count',
      key: 'professor_count',
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

  // 处理技术要素点击 - 跳转到技术要素页
  const handleTechElementClick = (techElementId: number) => {
    navigate(`/tech-element?tech_element_id=${techElementId}${country ? `&country_id=${country}` : ''}`)
  }

  // 处理区域变化
  const handleRegionChange = (value: string | undefined) => {
    setRegion(value)
    setCountry(undefined)
    setSchool(undefined)
  }

  // 处理搜索
  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 })
    // TODO: 调用API获取数据
  }

  // 处理重置
  const handleReset = () => {
    setRegion(undefined)
    setCountry(undefined)
    setSchool(undefined)
    setTechElement(undefined)
    setTechDirection(undefined)
    setKeyword('')
    setRoleType(undefined)
  }

  // 处理表格分页变化
  const handleTableChange = (newPagination: any) => {
    setPagination({
      ...pagination,
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    })
  }

  // 初始化加载 - 显示空状态提示
  useEffect(() => {
    // 页面骨架已就绪，等待API开发完成后接入真实数据
  }, [])

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
            <div style={{ marginBottom: 4 }}><Text type="secondary">区域</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择区域"
              value={region}
              onChange={handleRegionChange}
              options={regionOptions}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择国家"
              value={country}
              onChange={setCountry}
              options={region && countryOptions[region] ? countryOptions[region] : []}
              disabled={!region}
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
              value={school}
              onChange={setSchool}
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
              value={techElement}
              onChange={setTechElement}
              options={techElementOptions}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">技术方向</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择技术方向"
              value={techDirection}
              onChange={setTechDirection}
              disabled={!techElement}
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
          <Col span={6}>
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
          <TabPane tab="院校分布" key="school">
            <Table
              columns={schoolColumns}
              dataSource={schoolData}
              rowKey="school_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: region || country ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择区域或国家后查询" />
                ),
              }}
            />
          </TabPane>
          <TabPane tab="技术要素分布" key="tech-element">
            <Table
              columns={techElementColumns}
              dataSource={techElementData}
              rowKey="tech_element_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: region || country ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择区域或国家后查询" />
                ),
              }}
            />
          </TabPane>
          <TabPane tab="人才明细" key="talent">
            <Table
              columns={talentColumns}
              dataSource={talentData}
              rowKey="talent_id"
              loading={loading}
              pagination={pagination}
              onChange={handleTableChange}
              locale={{
                emptyText: region || country ? (
                  <Empty description="暂无数据，请调整筛选条件" />
                ) : (
                  <Empty description="请选择区域或国家后查询" />
                ),
              }}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default CountrySchoolPage

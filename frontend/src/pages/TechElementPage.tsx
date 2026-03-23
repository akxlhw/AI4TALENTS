/**
 * 技术要素页面 - MVP v1.1
 * 面向业务部门的主分析页面，从技术要素/技术方向看人才供给
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

const { Title, Text } = Typography
const { TabPane } = Tabs

// 国家分布数据类型
interface CountryDistribution {
  country_id: number
  country_name: string
  talent_count: number
  professor_count: number
  student_count: number
}

// 院校分布数据类型
interface SchoolDistribution {
  school_id: number
  school_name: string
  country_name: string
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

const TechElementPage: React.FC = () => {
  const navigate = useNavigate()

  // 筛选状态
  const [techElement, setTechElement] = useState<string | undefined>()
  const [techDirection, setTechDirection] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [country, setCountry] = useState<string | undefined>()
  const [school, setSchool] = useState<string | undefined>()
  const [roleType, setRoleType] = useState<string | undefined>()

  // 页面状态
  const [activeTab, setActiveTab] = useState('country')
  const [loading] = useState(false)
  const [summaryLoading] = useState(false)

  // 数据
  const [summary] = useState({
    talentCount: 0,
    professorCount: 0,
    studentCount: 0,
    schoolCount: 0,
    countryCount: 0,
  })
  const [countryData] = useState<CountryDistribution[]>([])
  const [schoolData] = useState<SchoolDistribution[]>([])
  const [talentData] = useState<TalentItem[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })

  // 模拟技术要素选项 - 后续从API获取
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

  // 处理国家点击 - 跳转到国家院校页
  const handleCountryClick = (countryId: number) => {
    navigate(`/country-school?country_id=${countryId}${techElement ? `&tech_element=${techElement}` : ''}`)
  }

  // 处理搜索
  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 })
    // TODO: 调用API获取数据
  }

  // 处理重置
  const handleReset = () => {
    setTechElement(undefined)
    setTechDirection(undefined)
    setKeyword('')
    setCountry(undefined)
    setSchool(undefined)
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
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择国家"
              value={country}
              onChange={setCountry}
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
          <TabPane tab="国家分布" key="country">
            <Table
              columns={countryColumns}
              dataSource={countryData}
              rowKey="country_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: techElement ? (
                  <Empty description="暂无数据，请选择技术要素后查询" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
                ),
              }}
            />
          </TabPane>
          <TabPane tab="院校分布" key="school">
            <Table
              columns={schoolColumns}
              dataSource={schoolData}
              rowKey="school_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              onChange={handleTableChange}
              locale={{
                emptyText: techElement ? (
                  <Empty description="暂无数据，请选择技术要素后查询" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
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
                emptyText: techElement ? (
                  <Empty description="暂无数据，请选择技术要素后查询" />
                ) : (
                  <Empty description="请选择技术要素后查询" />
                ),
              }}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default TechElementPage

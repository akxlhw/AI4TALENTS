import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Input, Typography, Tag, Space, Spin, Button, Divider } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  TeamOutlined,
  BankOutlined,
  UserOutlined,
  SearchOutlined,
  GlobalOutlined,
  AppstoreOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title, Paragraph, Text } = Typography
const { Search } = Input

// 热门技术要素（模拟数据，后续从API获取）
const HOT_TECH_ELEMENTS = [
  { id: 'ai', name: '人工智能', count: 156 },
  { id: 'ml', name: '机器学习', count: 128 },
  { id: 'nlp', name: '自然语言处理', count: 89 },
  { id: 'cv', name: '计算机视觉', count: 76 },
  { id: 'robotics', name: '机器人', count: 52 },
  { id: 'dl', name: '深度学习', count: 45 },
]

// 重点国家（模拟数据）
const KEY_COUNTRIES = [
  { id: 'us', name: '美国', count: 320 },
  { id: 'cn', name: '中国', count: 180 },
  { id: 'gb', name: '英国', count: 95 },
  { id: 'de', name: '德国', count: 72 },
  { id: 'jp', name: '日本', count: 58 },
]

// 重点院校（模拟数据）
const KEY_SCHOOLS = [
  { id: 1, name: 'MIT', count: 45 },
  { id: 2, name: 'Stanford', count: 42 },
  { id: 3, name: 'Harvard', count: 38 },
  { id: 4, name: '清华', count: 35 },
  { id: 5, name: 'Cambridge', count: 32 },
]

interface OverviewStats {
  stats: {
    school_count: number
    professor_count: number
    student_count: number
    talent_count: number
    tech_element_count?: number
    tech_direction_count?: number
    country_count?: number
  }
  version: string
  generated_at: string
}

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewStats | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const overviewRes = await api.overview.get()
      setOverview(overviewRes.data)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    if (value.trim()) {
      navigate(`/search?q=${encodeURIComponent(value.trim())}`)
    }
  }

  const handleTechElementClick = (techElementId: string) => {
    navigate(`/tech-element?tech_element=${techElementId}`)
  }

  const handleCountryClick = (countryId: string) => {
    navigate(`/country-school?country_id=${countryId}`)
  }

  const handleSchoolClick = (schoolId: number) => {
    navigate(`/country-school?school_id=${schoolId}`)
  }

  const stats = overview?.stats || {
    school_count: 0,
    professor_count: 0,
    student_count: 0,
    talent_count: 0,
    tech_element_count: 0,
    tech_direction_count: 0,
    country_count: 0,
  }

  return (
    <Spin spinning={loading}>
      <div>
        {/* 标题和描述 */}
        <div style={{ marginBottom: 24 }}>
          <Title level={2} style={{ margin: 0, marginBottom: 4 }}>智能学术界人才库</Title>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            基于OpenAlex学术数据库的人才发现平台 - 汇聚全球高校教授与学生信息
          </Paragraph>
        </div>

        {/* 基础统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="已收录高校"
                value={stats.school_count}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#1890ff', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="教授类人才"
                value={stats.professor_count}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#52c41a', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="学生类人才"
                value={stats.student_count}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#faad14', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="总人才数"
                value={stats.talent_count}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#722ed1', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="技术要素"
                value={stats.tech_element_count || HOT_TECH_ELEMENTS.length}
                prefix={<AppstoreOutlined />}
                valueStyle={{ color: '#13c2c2', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="覆盖国家"
                value={stats.country_count || KEY_COUNTRIES.length}
                prefix={<GlobalOutlined />}
                valueStyle={{ color: '#eb2f96', fontSize: 24 }}
              />
            </Card>
          </Col>
        </Row>

        {/* 搜索框 */}
        <Card style={{ marginBottom: 24 }}>
          <Search
            placeholder="输入姓名、学校、研究方向等关键词搜索人才..."
            enterButton={<><SearchOutlined /> 搜索人才</>}
            size="large"
            onSearch={handleSearch}
          />
          {overview && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              数据版本: {overview.version} | 更新时间: {overview.generated_at}
            </Text>
          )}
        </Card>

        {/* 主视角概要区 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          {/* 技术要素概要卡 */}
          <Col span={12}>
            <Card
              title={
                <Space>
                  <AppstoreOutlined style={{ color: '#1890ff' }} />
                  <span>技术要素视角</span>
                </Space>
              }
              extra={
                <Button type="link" onClick={() => navigate('/tech-element')}>
                  进入 <ArrowRightOutlined />
                </Button>
              }
              style={{ height: '100%' }}
            >
              {/* 概要统计 */}
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Statistic title="技术要素" value={stats.tech_element_count || HOT_TECH_ELEMENTS.length} />
                </Col>
                <Col span={8}>
                  <Statistic title="技术方向" value={stats.tech_direction_count || 24} />
                </Col>
                <Col span={8}>
                  <Statistic title="人才总数" value={stats.talent_count} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={12}>
                  <Statistic title="覆盖国家" value={stats.country_count || KEY_COUNTRIES.length} />
                </Col>
                <Col span={12}>
                  <Statistic title="覆盖院校" value={stats.school_count} />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              {/* 热门技术要素标签 */}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>热门技术要素：</Text>
                <div style={{ marginTop: 8 }}>
                  {HOT_TECH_ELEMENTS.slice(0, 6).map((item) => (
                    <Tag
                      key={item.id}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="blue"
                      onClick={() => handleTechElementClick(item.id)}
                    >
                      {item.name} ({item.count})
                    </Tag>
                  ))}
                </div>
              </div>
            </Card>
          </Col>

          {/* 国家院校概要卡 */}
          <Col span={12}>
            <Card
              title={
                <Space>
                  <GlobalOutlined style={{ color: '#52c41a' }} />
                  <span>国家院校视角</span>
                </Space>
              }
              extra={
                <Button type="link" onClick={() => navigate('/country-school')}>
                  进入 <ArrowRightOutlined />
                </Button>
              }
              style={{ height: '100%' }}
            >
              {/* 概要统计 */}
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Statistic title="覆盖国家" value={stats.country_count || KEY_COUNTRIES.length} />
                </Col>
                <Col span={8}>
                  <Statistic title="覆盖院校" value={stats.school_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="人才总数" value={stats.talent_count} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={12}>
                  <Statistic title="覆盖技术要素" value={stats.tech_element_count || HOT_TECH_ELEMENTS.length} />
                </Col>
                <Col span={12}>
                  <Statistic title="技术方向" value={stats.tech_direction_count || 24} />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              {/* 重点国家标签 */}
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>重点国家：</Text>
                <div style={{ marginTop: 8 }}>
                  {KEY_COUNTRIES.slice(0, 5).map((item) => (
                    <Tag
                      key={item.id}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="green"
                      onClick={() => handleCountryClick(item.id)}
                    >
                      {item.name} ({item.count})
                    </Tag>
                  ))}
                </div>
              </div>

              {/* 重点院校标签 */}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>重点院校：</Text>
                <div style={{ marginTop: 8 }}>
                  {KEY_SCHOOLS.slice(0, 5).map((item) => (
                    <Tag
                      key={item.id}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="orange"
                      onClick={() => handleSchoolClick(item.id)}
                    >
                      {item.name} ({item.count})
                    </Tag>
                  ))}
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  )
}

export default HomePage

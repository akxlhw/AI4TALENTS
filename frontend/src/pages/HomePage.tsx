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

interface OverviewStats {
  stats: {
    school_count: number
    professor_count: number
    student_count: number
    talent_count: number
    tech_element_count?: number
    country_count?: number
  }
  version: string
  generated_at: string
}

// 首页热点数据类型
interface HotTechElement {
  tech_element_id: number
  element_code: string
  element_name: string
  talent_count: number
}

interface TopCountry {
  country_code: string
  country_name: string | null
  talent_count: number
}

interface TopSchool {
  school_id: number
  school_name: string
  country_name: string | null
  talent_count: number
}

interface HomepageHighlights {
  hot_tech_elements: HotTechElement[]
  top_countries: TopCountry[]
  top_schools: TopSchool[]
  version: string
  generated_at: string
}

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [highlights, setHighlights] = useState<HomepageHighlights | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewRes, highlightsRes] = await Promise.all([
        api.overview.get(),
        api.homepage.getHighlights(),
      ])
      setOverview(overviewRes.data)
      setHighlights(highlightsRes.data)
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

  const handleTechElementClick = (techElementId: number) => {
    navigate(`/tech-element?tech_element_id=${techElementId}`)
  }

  const handleCountryClick = (countryCode: string) => {
    navigate(`/country-school?country_code=${countryCode}`)
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
    country_count: 0,
  }

  const hotTechElements = highlights?.hot_tech_elements || []
  const topCountries = highlights?.top_countries || []
  const topSchools = highlights?.top_schools || []

  return (
    <Spin spinning={loading}>
      <div>
        {/* 标题和描述 */}
        <div style={{ marginBottom: 24 }}>
          <Title level={2} style={{ margin: 0, marginBottom: 4 }}>智能学术界人才库</Title>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            基于学术界公开数据的人才发现平台 - 汇聚全球高校科研院所人才信息
          </Paragraph>
        </div>

        {/* 基础统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="已收录院校机构"
                value={stats.school_count}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#1890ff', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="教授/研究员"
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
                value={stats.tech_element_count || hotTechElements.length}
                prefix={<AppstoreOutlined />}
                valueStyle={{ color: '#13c2c2', fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="覆盖国家"
                value={stats.country_count || topCountries.length}
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
                  <span>技术要素</span>
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
                  <Statistic title="技术要素" value={stats.tech_element_count || hotTechElements.length} />
                </Col>
                <Col span={8}>
                  <Statistic title="人才总数" value={stats.talent_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="覆盖国家" value={stats.country_count || topCountries.length} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={12}>
                  <Statistic title="覆盖院校机构" value={stats.school_count} />
                </Col>
                <Col span={12}>
                  <Statistic title="教授/研究员" value={stats.professor_count} />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              {/* 热门技术要素标签 */}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>热门技术要素：</Text>
                <div style={{ marginTop: 8 }}>
                  {hotTechElements.slice(0, 6).map((item) => (
                    <Tag
                      key={item.tech_element_id}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="blue"
                      onClick={() => handleTechElementClick(item.tech_element_id)}
                    >
                      {item.element_name} ({item.talent_count})
                    </Tag>
                  ))}
                  {hotTechElements.length === 0 && (
                    <Text type="secondary">暂无数据</Text>
                  )}
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
                  <span>院校机构</span>
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
                  <Statistic title="覆盖国家" value={stats.country_count || topCountries.length} />
                </Col>
                <Col span={8}>
                  <Statistic title="覆盖院校机构" value={stats.school_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="人才总数" value={stats.talent_count} />
                </Col>
              </Row>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={12}>
                  <Statistic title="教授/研究员" value={stats.professor_count} />
                </Col>
                <Col span={12}>
                  <Statistic title="学生类人才" value={stats.student_count} />
                </Col>
              </Row>

              <Divider style={{ margin: '12px 0' }} />

              {/* 主要国家标签 */}
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>主要国家：</Text>
                <div style={{ marginTop: 8 }}>
                  {topCountries.slice(0, 5).map((item) => (
                    <Tag
                      key={item.country_code}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="green"
                      onClick={() => handleCountryClick(item.country_code)}
                    >
                      {item.country_name || item.country_code} ({item.talent_count})
                    </Tag>
                  ))}
                  {topCountries.length === 0 && (
                    <Text type="secondary">暂无数据</Text>
                  )}
                </div>
              </div>

              {/* Top院校标签 */}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Top院校机构：</Text>
                <div style={{ marginTop: 8 }}>
                  {topSchools.slice(0, 5).map((item) => (
                    <Tag
                      key={item.school_id}
                      style={{ marginBottom: 4, cursor: 'pointer' }}
                      color="orange"
                      onClick={() => handleSchoolClick(item.school_id)}
                    >
                      {item.school_name} ({item.talent_count})
                    </Tag>
                  ))}
                  {topSchools.length === 0 && (
                    <Text type="secondary">暂无数据</Text>
                  )}
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

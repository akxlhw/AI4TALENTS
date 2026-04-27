import { useState } from 'react'
import { Input, Typography, Tag, Space, Spin, Button, Row, Col, Card, Divider } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  SearchOutlined,
  GlobalOutlined,
  ArrowRightOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import { useHomepageHighlights, useOverviewStats } from '../hooks/useQueries'
import { useDomainStore } from '../stores/domainStore'
import { domainThemes } from '../theme'

const { Title, Paragraph, Text } = Typography
const { Search } = Input

interface HotTechDomain {
  tech_domain_id: number
  domain_code: string
  domain_name: string
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

/* ── Horizontal scroll row component ── */


const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const { currentDomain } = useDomainStore()
  const dt = domainThemes[currentDomain]

  const { data: overview, isLoading: overviewLoading } = useOverviewStats()
  const { data: highlights, isLoading: highlightsLoading } = useHomepageHighlights()

  const loading = overviewLoading || highlightsLoading
  const [searchValue, setSearchValue] = useState('')

  const handleSearch = (value: string) => {
    if (value.trim()) {
      navigate(`/search-recommend?tab=search&q=${encodeURIComponent(value.trim())}`)
    }
  }

  const handleTechDomainClick = (techDomainId: number) => {
    navigate(`/tech-domain?tech_domain_id=${techDomainId}`)
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
    tech_domain_count: 0,
    country_count: 0,
  }

  const hotTechDomains: HotTechDomain[] = highlights?.hot_tech_domains || []
  const topCountries: TopCountry[] = highlights?.top_countries || []
  const topSchools: TopSchool[] = highlights?.top_schools || []

  return (
    <Spin spinning={loading}>
      <div style={{ padding: '64px 0 100px' }}>
        {/* ═══════════ Hero Section ═══════════ */}
        <div
          style={{
            background: 'var(--domain-gradient)',
            padding: '72px 32px 56px',
            color: '#fff',
            position: 'relative',
            overflow: 'hidden',
            textAlign: 'center',
          }}
        >
          {/* Subtle pattern overlay */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              opacity: 0.06,
              backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)`,
              backgroundSize: '28px 28px',
            }}
          />
          <div style={{ position: 'relative', zIndex: 1, maxWidth: 640, margin: '0 auto' }}>
            <Title
              level={1}
              style={{
                margin: 0,
                marginBottom: 16,
                color: '#fff',
                fontWeight: 800,
                fontSize: 46,
                letterSpacing: '-0.5px',
              }}
            >
              智能学术界人才库
            </Title>
            <Paragraph
              style={{
                margin: 0,
                marginBottom: 40,
                color: 'rgba(255,255,255,0.85)',
                fontSize: 16,
              }}
            >
              基于学术界公开数据的人才发现平台 · 汇聚全球高校科研院所人才信息
            </Paragraph>
            <Search
              placeholder="输入姓名、学校、研究方向等关键词搜索人才..."
              enterButton={
                <span style={{ fontWeight: 500 }}>
                  <SearchOutlined /> 搜索
                </span>
              }
              size="large"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onSearch={handleSearch}
              style={{ maxWidth: 680, margin: '0 auto' }}
            />
            {/* Quick tags */}
            <Space
              wrap
              style={{ marginTop: 20, justifyContent: 'center' }}
              size={8}
            >
              {['深度学习', '自然语言处理', '计算机视觉', '强化学习', '量子计算'].map((tag) => (
                <Tag
                  key={tag}
                  onClick={() => handleSearch(tag)}
                  style={{
                    cursor: 'pointer',
                    background: 'rgba(255,255,255,0.15)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    color: 'rgba(255,255,255,0.9)',
                    borderRadius: 16,
                    padding: '2px 12px',
                    fontSize: 12,
                  }}
                >
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>
        </div>



        {/* ═══════════ Two-column Cards — v1.4.2 style ═══════════ */}
        <Row gutter={16} style={{ padding: '32px 32px 0' }} align="stretch">
          {/* Left — Tech Domains */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <Space>
                  <AppstoreOutlined style={{ color: dt.primary }} />
                  <span>技术领域</span>
                </Space>
              }
              extra={
                <Button type="link" size="small" onClick={() => navigate('/tech-domain')}>
                  查看全部 <ArrowRightOutlined />
                </Button>
              }
              style={{ marginBottom: 16, height: '100%' }}
            >
              {/* Overview stats — 5 dimensions */}
              <div style={{ marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border-secondary)' }}>
                <Space size={12} wrap>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    技术领域 <strong style={{ color: dt.primary }}>{stats.tech_domain_count || hotTechDomains.length}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    人才总数 <strong style={{ color: dt.primary }}>{stats.talent_count.toLocaleString()}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    覆盖国家 <strong style={{ color: dt.primary }}>{stats.country_count || topCountries.length}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    覆盖院校 <strong style={{ color: dt.primary }}>{stats.school_count.toLocaleString()}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    教授/研究员 <strong style={{ color: dt.primary }}>{stats.professor_count.toLocaleString()}</strong>
                  </Text>
                </Space>
              </div>

              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>热门技术领域</Text>
                <div style={{ marginTop: 6 }}>
                  {hotTechDomains.slice(0, 8).map((item) => (
                    <Tag
                      key={item.tech_domain_id}
                      style={{ marginBottom: 6, cursor: 'pointer', fontSize: 13, background: dt.lightBg, color: dt.primary, border: `1px solid ${dt.primary}33` }}
                      onClick={() => handleTechDomainClick(item.tech_domain_id)}
                    >
                      {item.domain_name} ({item.talent_count})
                    </Tag>
                  ))}
                  {hotTechDomains.length === 0 && (
                    <Text type="secondary">暂无数据</Text>
                  )}
                </div>
              </div>
            </Card>
          </Col>

          {/* Right — Schools */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <Space>
                  <GlobalOutlined style={{ color: dt.secondary }} />
                  <span>院校机构</span>
                </Space>
              }
              extra={
                <Button type="link" size="small" onClick={() => navigate('/country-school')}>
                  查看全部 <ArrowRightOutlined />
                </Button>
              }
              style={{ marginBottom: 16, height: '100%' }}
            >
              {/* Overview stats — 5 dimensions */}
              <div style={{ marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--border-secondary)' }}>
                <Space size={12} wrap>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    覆盖国家 <strong style={{ color: dt.secondary }}>{stats.country_count || topCountries.length}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    覆盖院校 <strong style={{ color: dt.secondary }}>{stats.school_count.toLocaleString()}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    人才总数 <strong style={{ color: dt.secondary }}>{stats.talent_count.toLocaleString()}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    教授/研究员 <strong style={{ color: dt.secondary }}>{stats.professor_count.toLocaleString()}</strong>
                  </Text>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    学生类人才 <strong style={{ color: dt.secondary }}>{stats.student_count.toLocaleString()}</strong>
                  </Text>
                </Space>
              </div>

              {/* Countries */}
              <div style={{ marginBottom: 10 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>人才分布 — 国家</Text>
                <div style={{ marginTop: 6 }}>
                  {topCountries.slice(0, 8).map((item) => (
                    <Tag
                      key={item.country_code}
                      style={{ marginBottom: 6, cursor: 'pointer', fontSize: 13, background: '#E8F4F8', color: dt.secondary, border: `1px solid ${dt.secondary}44` }}
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

              <Divider style={{ margin: '8px 0' }} />

              {/* Schools */}
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>顶尖院校机构</Text>
                <div style={{ marginTop: 6 }}>
                  {topSchools.slice(0, 8).map((item) => (
                    <Tag
                      key={item.school_id}
                      style={{ marginBottom: 6, cursor: 'pointer', fontSize: 13, background: '#F0F4F8', color: '#2D5A87', border: '1px solid #2D5A8733' }}
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

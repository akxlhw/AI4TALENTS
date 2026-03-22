import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Input, Typography, Tabs, Table, Tag, Space, Spin, Badge } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  TeamOutlined,
  BankOutlined,
  UserOutlined,
  SearchOutlined,
  GlobalOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title, Paragraph } = Typography
const { Search } = Input
const { TabPane } = Tabs

// 区域定义
const REGIONS: Record<string, { name: string; countries: string[] }> = {
  asia_pacific: {
    name: '亚太地区',
    countries: ['CN', 'JP', 'KR', 'SG', 'AU'],
  },
  europe: {
    name: '欧洲',
    countries: ['GB', 'DE', 'FR', 'CH', 'NL', 'SE', 'IT', 'ES'],
  },
  north_america: {
    name: '北美',
    countries: ['US', 'CA'],
  },
  other: {
    name: '其他地区',
    countries: [], // 其余国家
  },
}

interface OverviewStats {
  stats: {
    school_count: number
    professor_count: number
    student_count: number
    talent_count: number
  }
  version: string
  generated_at: string
}

interface School {
  school_id: number
  school_name: string
  school_alias: string | null
  country_id: number
  country_name: string | null
  country_code: string | null
  professor_count: number
  student_count: number
  homepage_url: string | null
}

interface Country {
  country_id: number
  country_code: string
  country_name_cn: string
  country_name_en: string | null
  school_count: number
  professor_count: number
}

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [schools, setSchools] = useState<School[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [activeRegion, setActiveRegion] = useState('north_america')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewRes, schoolsRes, countriesRes] = await Promise.all([
        api.overview.get(),
        api.schools.list({}),
        api.countries.list(),
      ])
      setOverview(overviewRes.data)
      setSchools(schoolsRes.data.items || [])
      setCountries(countriesRes.data.items || [])
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

  const getSchoolsByRegion = (regionKey: string): School[] => {
    const region = REGIONS[regionKey]
    if (!region) return []

    if (regionKey === 'other') {
      // 其他地区：不在任何已定义区域的国家
      const definedCountries = Object.values(REGIONS)
        .filter(r => r.countries.length > 0)
        .flatMap(r => r.countries)
      return schools.filter(s => !definedCountries.includes(s.country_code || ''))
    }

    return schools.filter(s => region.countries.includes(s.country_code || ''))
  }

  const getRegionStats = (regionKey: string) => {
    const regionSchools = getSchoolsByRegion(regionKey)
    return {
      schoolCount: regionSchools.length,
      professorCount: regionSchools.reduce((sum, s) => sum + (s.professor_count || 0), 0),
      studentCount: regionSchools.reduce((sum, s) => sum + (s.student_count || 0), 0),
    }
  }

  const stats = overview?.stats || {
    school_count: 0,
    professor_count: 0,
    student_count: 0,
    talent_count: 0,
  }

  const schoolColumns = [
    {
      title: '学校名称',
      dataIndex: 'school_name',
      key: 'school_name',
      render: (text: string, record: School) => (
        <a onClick={() => navigate(`/schools/${record.school_id}`)} style={{ fontWeight: 500 }}>
          {text}
        </a>
      ),
    },
    {
      title: '国家/地区',
      dataIndex: 'country_name',
      key: 'country_name',
      width: 120,
      render: (name: string, record: School) => (
        <Tag icon={<GlobalOutlined />} color="blue">
          {name || record.country_code}
        </Tag>
      ),
    },
    {
      title: '教授',
      dataIndex: 'professor_count',
      key: 'professor_count',
      width: 80,
      align: 'center' as const,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: '学生',
      dataIndex: 'student_count',
      key: 'student_count',
      width: 80,
      align: 'center' as const,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#faad14' }} />
      ),
    },
    {
      title: '主页',
      dataIndex: 'homepage_url',
      key: 'homepage_url',
      width: 80,
      align: 'center' as const,
      render: (url: string | null) =>
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            访问
          </a>
        ) : (
          <span style={{ color: '#ccc' }}>-</span>
        ),
    },
  ]

  return (
    <Spin spinning={loading}>
      <div>
        {/* 标题和描述 */}
        <Title level={2}>智能学术界人才库</Title>
        <Paragraph type="secondary">
          基于OpenAlex学术数据库的人才发现平台 - 汇聚全球高校教授与学生信息
        </Paragraph>

        {/* 统计总览 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="已收录高校"
                value={stats.school_count}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="教授类人才"
                value={stats.professor_count}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="学生类人才"
                value={stats.student_count}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总人才数"
                value={stats.talent_count}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#722ed1' }}
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
            <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
              数据版本: {overview.version} | 更新时间: {overview.generated_at}
            </Paragraph>
          )}
        </Card>

        {/* 区域学校列表 */}
        <Card title={<><BankOutlined style={{ marginRight: 8 }} />全球高校分布</>}>
          <Tabs activeKey={activeRegion} onChange={setActiveRegion}>
            {Object.entries(REGIONS).map(([key, region]) => {
              const regionStats = getRegionStats(key)
              return (
                <TabPane
                  key={key}
                  tab={
                    <Space>
                      <span>{region.name}</span>
                      <Badge count={regionStats.schoolCount} showZero style={{ backgroundColor: '#1890ff' }} />
                    </Space>
                  }
                >
                  <Table
                    dataSource={getSchoolsByRegion(key)}
                    columns={schoolColumns}
                    rowKey="school_id"
                    pagination={{ pageSize: 10, showSizeChanger: false }}
                    size="small"
                    locale={{ emptyText: '该区域暂无学校数据' }}
                  />
                </TabPane>
              )
            })}
          </Tabs>
        </Card>
      </div>
    </Spin>
  )
}

export default HomePage

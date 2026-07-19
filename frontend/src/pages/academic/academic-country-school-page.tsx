/**
 * 院校机构页面
 * 面向平台部门的主分析页面，以区域为第一分类维度展示院校机构
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { logger } from '../../utils/logger'
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
  Tabs,
  message,
} from 'antd'
import {
  ReloadOutlined,
  TeamOutlined,
  BankOutlined,
  GlobalOutlined,
  UserOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'

const { Title, Text } = Typography

// 区域定义 - 按北美、亚太、欧洲、其他顺序
const REGIONS_ORDER = ['north_america', 'asia_pacific', 'europe', 'other'] as const

const NORTH_AMERICA_CODES = new Set(['US', 'CA'])
const ASIA_PACIFIC_CODES = new Set(['CN', 'JP', 'KR', 'SG', 'AU', 'NZ', 'HK', 'MO', 'TW', 'IN', 'MY', 'TH'])
const EUROPE_CODES = new Set(['GB', 'DE', 'FR', 'CH', 'NL', 'IT', 'ES', 'SE', 'AT', 'BE', 'DK', 'FI', 'NO', 'IE', 'PT', 'PL'])

// 区域配置 - countries 数组会在运行时动态填充
const REGIONS: Record<string, { name: string; countries: string[] }> = {
  north_america: {
    name: '北美地区',
    countries: Array.from(NORTH_AMERICA_CODES)
  },
  asia_pacific: {
    name: '亚太地区',
    countries: Array.from(ASIA_PACIFIC_CODES)
  },
  europe: {
    name: '欧洲地区',
    countries: Array.from(EUROPE_CODES)
  },
  other: {
    name: '其他',
    countries: [] // 动态计算
  }
}

// 国家数据类型
interface Country {
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

const CountrySchoolPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // 筛选状态
  const [countryCode, setCountryCode] = useState<string | undefined>(
    searchParams.get('country_code') || undefined
  )
  const [schoolId, setSchoolId] = useState<number | undefined>(
    searchParams.get('school_id') ? Number(searchParams.get('school_id')) : undefined
  )
  const [keyword, setKeyword] = useState('')

  // 页面状态 - 默认显示北美地区
  const [activeRegion, setActiveRegion] = useState<string>('north_america')
  const [loading, setLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)

  // 数据
  const [countries, setCountries] = useState<Country[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [summary, setSummary] = useState({
    talentCount: 0,
    professorCount: 0,
    studentCount: 0,
    schoolCount: 0,
  })

  const otherRegionCountryCodes = useMemo(() => {
    const definedCodes = new Set([
      ...NORTH_AMERICA_CODES,
      ...ASIA_PACIFIC_CODES,
      ...EUROPE_CODES
    ])
    // 从实际获取的国家列表中，找出不属于任何已定义区域的国家
    return new Set(
      countries
        .filter(c => !definedCodes.has(c.country_code))
        .map(c => c.country_code)
    )
  }, [countries])

  // 当前区域的国家列表
  const currentRegionCountries = useMemo(() => {
    if (activeRegion === 'other') {
      return countries.filter(c => otherRegionCountryCodes.has(c.country_code))
    }
    const regionData = REGIONS[activeRegion]
    return countries.filter(c => regionData.countries.includes(c.country_code))
  }, [countries, activeRegion, otherRegionCountryCodes])

  // 根据筛选条件过滤院校
  const filteredSchools = useMemo(() => {
    let filtered = schools

    // 按当前区域筛选
    if (activeRegion === 'other') {
      filtered = filtered.filter(s =>
        otherRegionCountryCodes.has(s.country_code || '')
      )
    } else {
      const regionData = REGIONS[activeRegion]
      filtered = filtered.filter(s =>
        regionData.countries.includes(s.country_code || '')
      )
    }

    // 按国家筛选
    if (countryCode) {
      filtered = filtered.filter(s => s.country_code === countryCode)
    }

    // 按关键词筛选
    if (keyword) {
      filtered = filtered.filter(s =>
        s.school_name.toLowerCase().includes(keyword.toLowerCase())
      )
    }

    // 按人才数排序
    return filtered.sort((a, b) => (b.professor_count + b.student_count) - (a.professor_count + a.student_count))
  }, [schools, activeRegion, countryCode, keyword, otherRegionCountryCodes])

  const fetchCountries = useCallback(async () => {
    try {
      const response = await api.countries.list()
      setCountries(response.data.items || [])
    } catch (error) {
      logger.error('Failed to fetch countries:', error)
      message.error(getErrorMessage(error, '加载国家列表失败'))
    }
  }, [])

  // 加载学校列表（分页加载全量数据用于客户端区域筛选）
  const fetchSchools = useCallback(async () => {
    setLoading(true)
    try {
      let allItems: NonNullable<typeof schools> = []
      let page = 1
      let hasMore = true
      while (hasMore) {
        const response = await api.schools.list({ page, page_size: 200 })
        const items = response.data.items || []
        allItems = allItems.concat(items)
        hasMore = items.length >= 200
        page++
      }
      setSchools(allItems)
    } catch (error) {
      logger.error('Failed to fetch schools:', error)
      message.error(getErrorMessage(error, '加载院校列表失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true)
    try {
      const overviewRes = await api.overview.get()
      setSummary({
        talentCount: overviewRes.data.stats.talent_count,
        professorCount: overviewRes.data.stats.professor_count,
        studentCount: overviewRes.data.stats.student_count,
        schoolCount: overviewRes.data.stats.school_count,
      })
    } catch (error) {
      logger.error('Failed to fetch summary:', error)
      message.error(getErrorMessage(error, '加载统计数据失败'))
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCountries()
    fetchSummary()
    fetchSchools()
  }, [fetchCountries, fetchSchools, fetchSummary])

  // CR-01: 根据URL中的country_code自动切换区域标签
  useEffect(() => {
    if (countryCode) {
      // 查找国家所属区域
      if (NORTH_AMERICA_CODES.has(countryCode)) {
        setActiveRegion('north_america')
      } else if (ASIA_PACIFIC_CODES.has(countryCode)) {
        setActiveRegion('asia_pacific')
      } else if (EUROPE_CODES.has(countryCode)) {
        setActiveRegion('europe')
      } else if (otherRegionCountryCodes.has(countryCode)) {
        setActiveRegion('other')
      }
    }
  }, [countryCode, otherRegionCountryCodes])

  // 处理URL参数中的school_id - 自动跳转到学校详情页
  useEffect(() => {
    if (schoolId) {
      navigate(`/schools/${schoolId}`)
    }
  }, [schoolId, navigate])

  // 切换区域时重置国家筛选
  const handleRegionChange = (regionKey: string) => {
    setActiveRegion(regionKey)
    setCountryCode(undefined)
  }

  const handleReset = () => {
    setCountryCode(undefined)
    setSchoolId(undefined)
    setKeyword('')
  }

  // 国家选项
  const countryOptions = currentRegionCountries.map(c => ({
    value: c.country_code,
    label: c.country_name_cn,
  }))

  // 学校表格列
  const schoolColumns: ColumnsType<School> = [
    {
      title: '院校机构',
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
      title: '教授/研究员',
      dataIndex: 'professor_count',
      key: 'professor_count',
      sorter: true,
    },
    {
      title: '学生',
      dataIndex: 'student_count',
      key: 'student_count',
      sorter: true,
    },
  ]

  // Tab项
  const tabItems = useMemo(() => {
    return REGIONS_ORDER.map(regionKey => {
      let regionSchools: School[]
      if (regionKey === 'other') {
        regionSchools = schools.filter(s =>
          otherRegionCountryCodes.has(s.country_code || '')
        )
      } else {
        const regionData = REGIONS[regionKey]
        regionSchools = schools.filter(s =>
          regionData.countries.includes(s.country_code || '')
        )
      }
      return {
        key: regionKey,
        label: (
          <Space>
            <GlobalOutlined />
            {REGIONS[regionKey].name}
            <Tag color="blue" style={{ marginLeft: 4 }}>{regionSchools.length}</Tag>
          </Space>
        ),
      }
    })
  }, [schools, otherRegionCountryCodes])

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>院校机构</Title>
        <Text type="secondary">按区域分类展示院校机构</Text>
      </div>

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
                title="教授/研究员"
                value={summary.professorCount}
                prefix={<UserOutlined />}
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
                title="覆盖院校机构"
                value={summary.schoolCount}
                prefix={<BankOutlined />}
              />
            </Col>
          </Row>
        </Spin>
      </Card>

      {/* 筛选区 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">国家</Text></div>
            <Select
              style={{ width: '100%' }}
              placeholder="全部国家"
              value={countryCode}
              onChange={setCountryCode}
              options={countryOptions}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">关键词</Text></div>
            <Input
              placeholder="院校名称"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 4 }}><Text type="secondary">&nbsp;</Text></div>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 院校列表区 - 按区域Tab展示 */}
      <Card>
        <Tabs
          activeKey={activeRegion}
          onChange={handleRegionChange}
          items={tabItems}
        />
        <Table
          columns={schoolColumns}
          dataSource={filteredSchools}
          rowKey="school_id"
          loading={loading}
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 所院校` }}
          locale={{
            emptyText: <Empty description="该区域暂无院校数据" />,
          }}
        />
      </Card>
    </div>
  )
}

export default CountrySchoolPage

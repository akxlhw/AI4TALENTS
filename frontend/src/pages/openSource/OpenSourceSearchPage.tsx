import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Typography,
  Button,
  Input,
  Select,
  Segmented,
  Spin,
  Empty,
  Pagination,
  Form,
} from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  StarOutlined,
  HeartOutlined,
  HeartFilled,
  EnvironmentOutlined,
  BuildOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { OSDeveloper, OSSearchQuery } from '../../types'

const { Title, Text } = Typography

const TECH_ELEMENT_OPTIONS = [
  { value: 'ai', label: '人工智能' },
  { value: 'robotics', label: '机器人' },
  { value: 'data_science', label: '数据科学' },
  { value: 'networks', label: '网络与通信' },
  { value: 'systems', label: '系统与软件' },
  { value: 'security', label: '信息安全' },
]

const SORT_OPTIONS = [
  { value: 'stars_desc', label: 'Stars 降序' },
  { value: 'stars_asc', label: 'Stars 升序' },
  { value: 'name_asc', label: '名称升序' },
]

const OpenSourceSearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [developers, setDevelopers] = useState<OSDeveloper[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set())
  const [filterExpanded, setFilterExpanded] = useState(false)

  const [query, setQuery] = useState<OSSearchQuery>({
    q: searchParams.get('q') || '',
    tech_elements: searchParams.get('tech_elements')?.split(',').filter(Boolean) || [],
    languages: searchParams.get('languages')?.split(',').filter(Boolean) || [],
    location: searchParams.get('location') || '',
    company: searchParams.get('company') || '',
    min_stars: searchParams.get('min_stars') ? parseInt(searchParams.get('min_stars')!) : undefined,
    sort_by: searchParams.get('sort_by') || 'stars_desc',
    mode: (searchParams.get('mode') as OSSearchQuery['mode']) || 'keyword',
    page: parseInt(searchParams.get('page') || '1'),
    page_size: 20,
  })

  const fetchDevelopers = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.openSource.listDevelopers({
        q: query.q,
        tech_elements: query.tech_elements,
        languages: query.languages,
        location: query.location,
        company: query.company,
        min_stars: query.min_stars,
        sort_by: query.sort_by,
        page: query.page,
        page_size: query.page_size,
      })
      setDevelopers(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      console.error('Search failed')
    } finally {
      setLoading(false)
    }
  }, [query])

  const fetchFavoriteIds = useCallback(async () => {
    try {
      const res = await api.openSource.getFavoriteIds()
      setFavoriteIds(new Set(res.data.developer_ids || []))
    } catch (e) {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchDevelopers()
    fetchFavoriteIds()
  }, [fetchDevelopers, fetchFavoriteIds])

  const updateSearchParams = (newQuery: OSSearchQuery) => {
    const params = new URLSearchParams()
    if (newQuery.q) params.set('q', newQuery.q)
    if (newQuery.tech_elements?.length) params.set('tech_elements', newQuery.tech_elements.join(','))
    if (newQuery.languages?.length) params.set('languages', newQuery.languages.join(','))
    if (newQuery.location) params.set('location', newQuery.location)
    if (newQuery.company) params.set('company', newQuery.company)
    if (newQuery.min_stars) params.set('min_stars', String(newQuery.min_stars))
    if (newQuery.sort_by && newQuery.sort_by !== 'stars_desc') params.set('sort_by', newQuery.sort_by)
    if (newQuery.mode && newQuery.mode !== 'keyword') params.set('mode', newQuery.mode)
    if (newQuery.page && newQuery.page > 1) params.set('page', String(newQuery.page))
    setSearchParams(params)
  }

  const handleSearch = () => {
    const newQuery = { ...query, page: 1 }
    setQuery(newQuery)
    updateSearchParams(newQuery)
  }

  const handlePageChange = (page: number) => {
    const newQuery = { ...query, page }
    setQuery(newQuery)
    updateSearchParams(newQuery)
  }

  const handleToggleFavorite = async (developerId: number) => {
    try {
      if (favoriteIds.has(developerId)) {
        await api.openSource.removeFavorite(developerId)
        setFavoriteIds((prev) => {
          const next = new Set(prev)
          next.delete(developerId)
          return next
        })
      } else {
        await api.openSource.addFavorite(developerId)
        setFavoriteIds((prev) => new Set(prev).add(developerId))
      }
    } catch (e) {
      console.error('Favorite toggle failed', e)
    }
  }

  const primary = '#2D3748'
  

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3} style={{ marginBottom: 16 }}>开源人才搜索</Title>

      {/* Search & Filter */}
      <Card className="domain-card" style={{ marginBottom: 16 }} bodyStyle={{ padding: 20 }}>
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Input
            size="large"
            placeholder="搜索开发者、技术栈、公司..."
            prefix={<SearchOutlined />}
            value={query.q}
            onChange={(e) => setQuery({ ...query, q: e.target.value })}
            onPressEnter={handleSearch}
          />
          <Button type="primary" size="large" onClick={handleSearch} style={{ background: primary, borderColor: primary }}>
            搜索
          </Button>
        </Space.Compact>

        <Space wrap style={{ marginBottom: 8 }}>
          <Button
            icon={<FilterOutlined />}
            onClick={() => setFilterExpanded(!filterExpanded)}
          >
            {filterExpanded ? '收起筛选' : '展开筛选'}
          </Button>
          <Segmented
            value={query.mode}
            onChange={(v) => setQuery({ ...query, mode: v as OSSearchQuery['mode'] })}
            options={[
              { label: '关键词', value: 'keyword' },
              { label: '语义', value: 'semantic' },
              { label: '混合', value: 'hybrid' },
            ]}
          />
          <Select
            value={query.sort_by}
            onChange={(v) => setQuery({ ...query, sort_by: v })}
            style={{ width: 140 }}
            options={SORT_OPTIONS}
          />
        </Space>

        {filterExpanded && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}>
              <Form.Item label="技术领域" style={{ marginBottom: 8 }}>
                <Select
                  mode="multiple"
                  placeholder="选择技术领域"
                  value={query.tech_elements}
                  onChange={(v) => setQuery({ ...query, tech_elements: v })}
                  style={{ width: '100%' }}
                  options={TECH_ELEMENT_OPTIONS}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="地区" style={{ marginBottom: 8 }}>
                <Input
                  placeholder="如: Beijing"
                  value={query.location}
                  onChange={(e) => setQuery({ ...query, location: e.target.value })}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="公司" style={{ marginBottom: 8 }}>
                <Input
                  placeholder="如: Microsoft"
                  value={query.company}
                  onChange={(e) => setQuery({ ...query, company: e.target.value })}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="最小 Stars" style={{ marginBottom: 8 }}>
                <Input
                  type="number"
                  placeholder="0"
                  value={query.min_stars}
                  onChange={(e) => setQuery({ ...query, min_stars: e.target.value ? parseInt(e.target.value) : undefined })}
                />
              </Form.Item>
            </Col>
          </Row>
        )}
      </Card>

      {/* Results */}
      <Text style={{ marginBottom: 16, display: 'block', color: 'var(--text-secondary)' }}>
        共 {total} 条结果
      </Text>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : developers.length === 0 ? (
        <Empty description="未找到符合条件的开发者" />
      ) : (
        <>
          <Row gutter={16}>
            {developers.map((dev) => (
              <Col span={8} key={dev.developer_id} style={{ marginBottom: 16 }}>
                <Card
                  hoverable
                  className="domain-card"
                  bodyStyle={{ padding: 20 }}
                  onClick={() => navigate(`/opensource/developers/${dev.developer_id}`)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Space align="start">
                      {dev.avatar_url ? (
                        <img
                          src={`${dev.avatar_url}${dev.avatar_url.includes('?') ? '&' : '?'}s=64`}
                          alt={dev.name || dev.github_login}
                          loading="lazy"
                          style={{ width: 48, height: 48, borderRadius: 24, objectFit: 'cover' }}
                        />
                      ) : (
                        <div style={{ width: 48, height: 48, borderRadius: 24, background: primary, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 18, fontWeight: 600 }}>
                          {(dev.name || dev.github_login)?.[0]?.toUpperCase()}
                        </div>
                      )}
                      <div>
                        <Text strong style={{ fontSize: 16, display: 'block' }}>
                          {dev.name || dev.github_login}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 13 }}>
                          @{dev.github_login}
                        </Text>
                      </div>
                    </Space>
                    <Button
                      type="text"
                      icon={favoriteIds.has(dev.developer_id) ? <HeartFilled style={{ color: '#F56565' }} /> : <HeartOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleToggleFavorite(dev.developer_id)
                      }}
                    />
                  </div>

                  <div style={{ marginTop: 12, marginBottom: 12 }}>
                    <Space wrap size={4}>
                      {(dev.primary_languages || []).slice(0, 4).map((lang) => (
                        <Tag key={lang} style={{ fontSize: 11, borderRadius: 4 }}>{lang}</Tag>
                      ))}
                      {(dev.tech_tags || []).slice(0, 3).map((tag) => (
                        <Tag key={tag} color="success" style={{ fontSize: 11, borderRadius: 4 }}>{tag}</Tag>
                      ))}
                    </Space>
                  </div>

                  <Row gutter={16}>
                    <Col span={8}>
                      <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                        <StarOutlined style={{ marginRight: 4 }} />Stars
                      </Text>
                      <div style={{ fontWeight: 700, color: primary }}>
                        {dev.total_stars_received}
                      </div>
                    </Col>
                    <Col span={8}>
                      <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                        <BuildOutlined style={{ marginRight: 4 }} />公司
                      </Text>
                      <div style={{ fontWeight: 700, color: primary, fontSize: 13 }}>
                        {dev.company || '-'}
                      </div>
                    </Col>
                    <Col span={8}>
                      <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                        <EnvironmentOutlined style={{ marginRight: 4 }} />地区
                      </Text>
                      <div style={{ fontWeight: 700, color: primary, fontSize: 13 }}>
                        {dev.location || '-'}
                      </div>
                    </Col>
                  </Row>
                </Card>
              </Col>
            ))}
          </Row>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
            <Pagination
              current={query.page}
              pageSize={query.page_size}
              total={total}
              onChange={handlePageChange}
              showSizeChanger={false}
            />
          </div>
        </>
      )}
    </div>
  )
}

export default OpenSourceSearchPage

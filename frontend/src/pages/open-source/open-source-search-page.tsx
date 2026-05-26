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
  Tooltip,
  Checkbox,
  message,
} from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  StarOutlined,
  HeartOutlined,
  HeartFilled,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import { semanticColors, domainThemes } from '../../theme'
import type { OSDeveloper, OSSearchQuery } from '../../types'

const { Title, Text, Paragraph } = Typography

const TECH_ELEMENT_OPTIONS = [
  { value: 'ai', label: '人工智能' },
  { value: 'robotics', label: '机器人' },
  { value: 'data_science', label: '数据科学' },
  { value: 'networks', label: '网络与通信' },
  { value: 'systems', label: '系统与软件' },
  { value: 'security', label: '信息安全' },
]

const LANGUAGE_OPTIONS = [
  { value: 'Python', label: 'Python' },
  { value: 'JavaScript', label: 'JavaScript' },
  { value: 'TypeScript', label: 'TypeScript' },
  { value: 'Go', label: 'Go' },
  { value: 'Rust', label: 'Rust' },
  { value: 'C++', label: 'C++' },
  { value: 'C', label: 'C' },
  { value: 'Java', label: 'Java' },
  { value: 'C#', label: 'C#' },
  { value: 'Shell', label: 'Shell' },
  { value: 'Ruby', label: 'Ruby' },
  { value: 'PHP', label: 'PHP' },
  { value: 'Swift', label: 'Swift' },
  { value: 'Kotlin', label: 'Kotlin' },
  { value: 'Scala', label: 'Scala' },
  { value: 'R', label: 'R' },
  { value: 'Julia', label: 'Julia' },
  { value: 'CUDA', label: 'CUDA' },
  { value: 'Lua', label: 'Lua' },
  { value: 'Haskell', label: 'Haskell' },
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
    repo_full_names: searchParams.get('repo_full_names')?.split(',').filter(Boolean) || [],
    is_committer: searchParams.get('is_committer') === 'true',
    sort_by: searchParams.get('sort_by') || 'stars_desc',
    mode: (searchParams.get('mode') as OSSearchQuery['mode']) || 'keyword',
    page: parseInt(searchParams.get('page') || '1'),
    page_size: 20,
  })

  const [repoOptions, setRepoOptions] = useState<{ value: string; label: string }[]>([])
  const [repoLoading, setRepoLoading] = useState(false)

  const fetchDevelopers = useCallback(async () => {
    try {
      setLoading(true)
      let res
      if (query.mode === 'keyword') {
        res = await api.openSource.listDevelopers({
          q: query.q,
          tech_elements: query.tech_elements,
          languages: query.languages,
          location: query.location,
          company: query.company,
          repo_full_names: query.repo_full_names,
          is_committer: query.is_committer,
          sort_by: query.sort_by,
          page: query.page,
          page_size: query.page_size,
        })
      } else {
        res = await api.openSource.search({
          q: query.q,
          mode: query.mode,
          filters: {
            tech_elements: query.tech_elements,
            languages: query.languages,
            location: query.location,
            company: query.company,
            repo_full_names: query.repo_full_names,
          },
          sort_by: query.sort_by,
          page: query.page,
          page_size: query.page_size,
        })
      }
      setDevelopers(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (err) {
      console.error('Search failed', err)
    } finally {
      setLoading(false)
    }
  }, [query])

  const loadRepos = useCallback(async (techElements: string[]) => {
    if (!techElements?.length) {
      setRepoOptions([])
      return
    }
    try {
      setRepoLoading(true)
      const res = await api.openSource.listRepositories({
        tech_elements: techElements,
        page_size: 100,
      })
      const items = res.data.items || []
      setRepoOptions(items.map((item: { repo_full_name: string }) => ({
        value: item.repo_full_name,
        label: item.repo_full_name,
      })))
    } catch (err) {
      console.error('Failed to load repos', err)
      setRepoOptions([])
    } finally {
      setRepoLoading(false)
    }
  }, [])

  const fetchFavoriteIds = useCallback(async () => {
    try {
      const res = await api.openSource.getFavoriteIds()
      setFavoriteIds(new Set(res.data.developer_ids || []))
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchDevelopers()
    fetchFavoriteIds()
  }, [fetchDevelopers, fetchFavoriteIds])

  useEffect(() => {
    if (query.tech_elements?.length) {
      loadRepos(query.tech_elements)
    } else {
      setRepoOptions([])
    }
  }, [query.tech_elements, loadRepos])

  const updateSearchParams = (newQuery: OSSearchQuery) => {
    const params = new URLSearchParams()
    if (newQuery.q) params.set('q', newQuery.q)
    if (newQuery.tech_elements?.length) params.set('tech_elements', newQuery.tech_elements.join(','))
    if (newQuery.languages?.length) params.set('languages', newQuery.languages.join(','))
    if (newQuery.location) params.set('location', newQuery.location)
    if (newQuery.company) params.set('company', newQuery.company)
    if (newQuery.repo_full_names?.length) params.set('repo_full_names', newQuery.repo_full_names.join(','))

    if (newQuery.is_committer) params.set('is_committer', 'true')
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
      message.error(getErrorMessage(e, '收藏操作失败'))
    }
  }

  const primary = domainThemes.opensource.primary
  

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3} style={{ marginBottom: 16 }}>开源人才搜索</Title>

      {/* Search & Filter */}
      <Card className="domain-card" style={{ marginBottom: 16 }} styles={{ body: { padding: 20 } }}>
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
                  onChange={(v) => {
                    const newQuery = { ...query, tech_elements: v, repo_full_names: [] as string[], page: 1 }
                    setQuery(newQuery)
                    updateSearchParams(newQuery)
                  }}
                  style={{ width: '100%' }}
                  options={TECH_ELEMENT_OPTIONS}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="关联仓库" style={{ marginBottom: 8 }}>
                <Select
                  mode="multiple"
                  placeholder={query.tech_elements?.length ? '选择仓库' : '请先选择技术领域'}
                  value={query.repo_full_names}
                  onChange={(v) => {
                    const newQuery = { ...query, repo_full_names: v, page: 1 }
                    setQuery(newQuery)
                    updateSearchParams(newQuery)
                  }}
                  style={{ width: '100%' }}
                  options={repoOptions}
                  loading={repoLoading}
                  disabled={!query.tech_elements?.length}
                  allowClear
                  showSearch
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
              <Form.Item label="编程语言" style={{ marginBottom: 8 }}>
                <Select
                  mode="multiple"
                  placeholder="选择编程语言"
                  value={query.languages}
                  onChange={(v) => setQuery({ ...query, languages: v })}
                  style={{ width: '100%' }}
                  options={LANGUAGE_OPTIONS}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="角色筛选" style={{ marginBottom: 8 }}>
                <Checkbox
                  checked={query.is_committer}
                  onChange={(e) => setQuery({ ...query, is_committer: e.target.checked })}
                >
                  Committer
                </Checkbox>
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
                  style={{ borderLeft: `3px solid ${domainThemes.opensource.secondary}`, transition: 'all 0.2s ease' }}
                  styles={{ body: { padding: '14px 16px' } }}
                  onClick={() => navigate(`/opensource/developers/${dev.developer_id}`)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <Space align="start">
                      {dev.avatar_url ? (
                        <img
                          src={`${dev.avatar_url}${dev.avatar_url.includes('?') ? '&' : '?'}s=64`}
                          alt={dev.name || dev.github_login}
                          loading="lazy"
                          style={{ width: 40, height: 40, borderRadius: 20, objectFit: 'cover' }}
                        />
                      ) : (
                        <div style={{ width: 40, height: 40, borderRadius: 20, background: primary, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 16, fontWeight: 600 }}>
                          {(dev.name || dev.github_login)?.[0]?.toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                          <Text strong style={{ fontSize: 14 }}>
                            {dev.name || dev.github_login}
                          </Text>
                          {dev.roles?.includes('Owner') && (
                            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 6px', borderRadius: 4, margin: 0, background: semanticColors.osYellow, color: '#fff', border: 'none', fontWeight: 600 }}>
                              Owner
                            </Tag>
                          )}
                          {dev.roles?.includes('Committer') && (
                            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 6px', borderRadius: 4, margin: 0, background: semanticColors.osBlue, color: '#fff', border: 'none', fontWeight: 600 }}>
                              Committer
                            </Tag>
                          )}
                        </div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          @{dev.github_login}
                        </Text>
                      </div>
                    </Space>
                    <Button
                      type="text"
                      size="small"
                      style={{ padding: '0 4px', margin: 0, flexShrink: 0 }}
                      icon={favoriteIds.has(dev.developer_id) ? <HeartFilled style={{ color: semanticColors.red }} /> : <HeartOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleToggleFavorite(dev.developer_id)
                      }}
                    />
                  </div>

                  <Paragraph
                    ellipsis={{ rows: 1 }}
                    style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}
                  >
                    {dev.bio || '暂无简介'}
                  </Paragraph>

                  <Row gutter={16}>
                    <Col span={6}>
                      <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Stars</Text>
                      <div style={{ fontWeight: 700, color: primary, fontSize: 13 }}>
                        <StarOutlined style={{ fontSize: 11, marginRight: 2 }} />
                        {(dev.total_stars_received / 1000).toFixed(1)}k
                      </div>
                    </Col>
                    <Col span={6}>
                      <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>开发语言</Text>
                      <Tooltip
                        title={
                          <Space size={4} wrap>
                            {(dev.primary_languages || []).map((lang) => (
                              <Tag key={lang} style={{ fontSize: 11, borderRadius: 4, margin: 0 }}>{lang}</Tag>
                            ))}
                            {(dev.primary_languages || []).length === 0 && '无'}
                          </Space>
                        }
                      >
                        <div style={{ fontWeight: 700, color: primary, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {(dev.primary_languages || []).slice(0, 2).join(', ') || '-'}
                        </div>
                      </Tooltip>
                    </Col>
                    <Col span={6}>
                      <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>公司</Text>
                      <div style={{ fontWeight: 700, color: primary, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {dev.company || '-'}
                      </div>
                    </Col>
                    <Col span={6}>
                      <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>地区</Text>
                      <div style={{ fontWeight: 700, color: primary, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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

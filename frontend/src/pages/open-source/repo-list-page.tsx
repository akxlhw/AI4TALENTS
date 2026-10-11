import { useEffect, useState, useCallback } from 'react'
import { semanticColors } from '../../theme'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import '@/i18n/namespaces/open-source'
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
  Spin,
  Empty,
  Pagination,
} from 'antd'
import {
  GithubOutlined,
  StarOutlined,
  FireOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { OSRepoConfig } from '../../types'
import {
  TECH_ELEMENT_GROUPS,
  getTechElementColor,
  useTechElements,
} from '@/constants/tech-elements'

const { Title, Text, Paragraph } = Typography

const RepoListPage: React.FC = () => {
  const { t } = useTranslation('openSource')
  // taxonomy 命名空间翻译 TECH_ELEMENT_GROUPS 的 i18n key（域分组 + 要素标签）
  const { t: tTax } = useTranslation('taxonomy')
  const { fullLabel } = useTechElements()
  const navigate = useNavigate()
  const [repos, setRepos] = useState<OSRepoConfig[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [techElement, setTechElement] = useState<string | undefined>(undefined)
  const [sortBy, setSortBy] = useState('stars')

  const techElementOptions = TECH_ELEMENT_GROUPS.map(g => ({
    label: tTax(g.label),
    options: g.options.map(o => ({ ...o, label: tTax(o.label) })),
  }))

  const sortOptions = [
    { value: 'stars', label: t('sort.starsDesc') },
    { value: 'id_desc', label: t('sort.newest') },
  ]

  const fetchRepos = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
      }
      if (techElement) params.tech_element = techElement
      if (searchKeyword) params.q = searchKeyword
      const res = await api.openSource.listRepositories(params)
      setRepos(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, techElement, searchKeyword, sortBy])

  useEffect(() => {
    fetchRepos()
  }, [fetchRepos])

  const handleSearch = () => {
    setPage(1)
    fetchRepos()
  }

  return (
    <div style={{ padding: '88px 32px 24px' }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/opensource')}
        style={{ marginBottom: 16, padding: 0 }}
      >
        {t('repo.backToEco')}
      </Button>

      <Title level={3} style={{ marginBottom: 24 }}>
        <FireOutlined style={{ marginRight: 8, color: semanticColors.osOrange }} />
        {t('repo.listTitle')}
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Input.Search
              placeholder={t('repo.searchPlaceholder')}
              allowClear
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onSearch={handleSearch}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder={t('repo.techPlaceholder')}
              allowClear
              showSearch
              optionFilterProp="label"
              style={{ width: '100%' }}
              value={techElement}
              onChange={(v) => { setTechElement(v); setPage(1) }}
              options={techElementOptions}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder={t('repo.sortPlaceholder')}
              style={{ width: '100%' }}
              value={sortBy}
              onChange={(v) => { setSortBy(v); setPage(1) }}
              options={sortOptions}
            />
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Button type="primary" onClick={handleSearch} block>
              {t('repo.query')}
            </Button>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        {repos.length === 0 ? (
          <Empty description={t('repo.empty')} />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {repos.map((repo) => (
                <Col xs={24} sm={12} lg={8} key={repo.repo_config_id}>
                  <Card
                    hoverable
                    className="domain-card"
                    styles={{ body: { padding: '16px 20px' } }}
                    style={{
                      borderLeft: `3px solid ${semanticColors.osOrange}`,
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                      height: '100%',
                    }}
                    onClick={() => {
                      const parts = repo.repo_full_name.split('/')
                      if (parts.length === 2) {
                        navigate(`/opensource/repos/${parts[0]}/${parts[1]}`)
                      }
                    }}
                  >
                    <Space style={{ marginBottom: 8 }}>
                      <GithubOutlined style={{ fontSize: 16 }} />
                      <Text strong style={{ fontSize: 14, fontFamily: 'monospace' }}>
                        {repo.repo_full_name}
                      </Text>
                    </Space>
                    <Paragraph
                      ellipsis={{ rows: 2 }}
                      style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, minHeight: 40 }}
                    >
                      {repo.description || repo.display_name || t('repo.noDescription')}
                    </Paragraph>
                    <Space size={12} wrap>
                      <Text style={{ fontSize: 12 }}>
                        <StarOutlined style={{ color: semanticColors.osOrange, marginRight: 4 }} />
                        {repo.stars_count || 0}
                      </Text>
                      {(Array.isArray(repo.tech_element) ? repo.tech_element : [repo.tech_element]).map(
                        (code) => (
                          <Tag
                            key={code}
                            color={getTechElementColor(code)}
                            style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}
                          >
                            {fullLabel(code)}
                          </Tag>
                        )
                      )}
                      {repo.language && (
                        <Tag style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>
                          {repo.language}
                        </Tag>
                      )}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                showTotal={count => t('repo.totalRepos', { n: count })}
                onChange={(p) => setPage(p)}
              />
            </div>
          </>
        )}
      </Spin>
    </div>
  )
}

export default RepoListPage

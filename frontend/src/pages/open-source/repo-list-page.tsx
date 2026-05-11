import { useEffect, useState, useCallback } from 'react'
import { semanticColors } from '../../theme'
import { useNavigate } from 'react-router-dom'
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

const { Title, Text, Paragraph } = Typography

const TECH_ELEMENT_OPTIONS = [
  { value: 'ai', label: '人工智能' },
  { value: 'robotics', label: '机器人' },
  { value: 'data_science', label: '数据科学' },
  { value: 'networks', label: '网络与通信' },
  { value: 'systems', label: '系统与软件' },
  { value: 'security', label: '信息安全' },
]

const SORT_OPTIONS = [
  { value: 'stars', label: 'Stars 降序' },
  { value: 'id_desc', label: '最新添加' },
]

const getTechElementLabel = (code: string) => {
  const item = TECH_ELEMENT_OPTIONS.find((t) => t.value === code)
  return item?.label || code
}

const getTechElementColor = (code: string) => {
  const colors: Record<string, string> = {
    ai: semanticColors.osPurple,
    robotics: semanticColors.osGreen,
    data_science: semanticColors.osBlue,
    networks: semanticColors.osOrangeDark,
    systems: semanticColors.osPurple,
    security: semanticColors.osRed,
  }
  return colors[code] || semanticColors.textGray
}

const RepoListPage: React.FC = () => {
  const navigate = useNavigate()
  const [repos, setRepos] = useState<OSRepoConfig[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [techElement, setTechElement] = useState<string | undefined>(undefined)
  const [sortBy, setSortBy] = useState('stars')

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
        返回开源生态
      </Button>

      <Title level={3} style={{ marginBottom: 24 }}>
        <FireOutlined style={{ marginRight: 8, color: semanticColors.osOrange }} />
        代码仓库列表
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Input.Search
              placeholder="搜索仓库名称..."
              allowClear
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onSearch={handleSearch}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder="技术领域"
              allowClear
              style={{ width: '100%' }}
              value={techElement}
              onChange={(v) => { setTechElement(v); setPage(1) }}
              options={TECH_ELEMENT_OPTIONS}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder="排序方式"
              style={{ width: '100%' }}
              value={sortBy}
              onChange={(v) => { setSortBy(v); setPage(1) }}
              options={SORT_OPTIONS}
            />
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Button type="primary" onClick={handleSearch} block>
              查询
            </Button>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        {repos.length === 0 ? (
          <Empty description="暂无仓库数据" />
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
                      {repo.description || repo.display_name || '暂无描述'}
                    </Paragraph>
                    <Space size={12} wrap>
                      <Text style={{ fontSize: 12 }}>
                        <StarOutlined style={{ color: semanticColors.osOrange, marginRight: 4 }} />
                        {repo.stars_count || 0}
                      </Text>
                      <Tag
                        color={getTechElementColor(repo.tech_element)}
                        style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}
                      >
                        {getTechElementLabel(repo.tech_element)}
                      </Tag>
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
                showTotal={(t) => `共 ${t} 个仓库`}
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

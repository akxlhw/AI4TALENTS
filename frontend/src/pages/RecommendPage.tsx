/**
 * Recommend Page - v1.4
 *
 * 功能说明：
 * - 基于参考人才推荐相似人才
 * - 显示推荐原因和相似度分数
 */
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Typography,
  Select,
  Button,
  Space,
  Table,
  Tag,
  Empty,
  Spin,
  Row,
  Col,
  message,
  Alert,
  InputNumber,
  List,
  Tooltip,
  Badge,
} from 'antd'
import {
  TeamOutlined,
  BulbOutlined,
  ReloadOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import type { RecommendResultItem, SearchTalent } from '../types'

const { Title, Text } = Typography

const RecommendPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // State
  const [referenceTalentIds, setReferenceTalentIds] = useState<number[]>([])
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(false)
  const [talentOptions, setTalentOptions] = useState<SearchTalent[]>([])
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<RecommendResultItem[]>([])
  const [tookMs, setTookMs] = useState<number | null>(null)

  // Initialize from URL params
  useEffect(() => {
    const talentId = searchParams.get('talent_id')
    if (talentId) {
      setReferenceTalentIds([parseInt(talentId, 10)])
    }
  }, [searchParams])

  // Search talents for selection
  const handleSearchTalents = async (query: string) => {
    if (!query.trim()) {
      setTalentOptions([])
      return
    }

    setSearching(true)
    try {
      const response = await api.talents.list({ keyword: query, page_size: 10 })
      setTalentOptions(response.data.items || [])
    } catch (error) {
      console.error('Search talents failed:', error)
    } finally {
      setSearching(false)
    }
  }

  // Add reference talent
  const handleAddTalent = (talentId: number) => {
    if (referenceTalentIds.includes(talentId)) {
      message.warning('该人才已添加')
      return
    }
    if (referenceTalentIds.length >= 10) {
      message.warning('最多添加10位参考人才')
      return
    }
    setReferenceTalentIds([...referenceTalentIds, talentId])
    setTalentOptions([])
  }

  // Remove reference talent
  const handleRemoveTalent = (talentId: number) => {
    setReferenceTalentIds(referenceTalentIds.filter(id => id !== talentId))
  }

  // Get recommendations
  const handleGetRecommendations = async () => {
    if (referenceTalentIds.length === 0) {
      message.warning('请至少添加一位参考人才')
      return
    }

    setLoading(true)
    try {
      const response = await api.recommend.getRecommendations({
        reference_talent_ids: referenceTalentIds,
        limit,
      })
      setResults(response.data.items || [])
      setTookMs(response.data.took_ms)
      message.success(`找到 ${response.data.total} 位推荐候选人`)
    } catch (error: unknown) {
      console.error('Get recommendations failed:', error)
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '获取推荐失败')
    } finally {
      setLoading(false)
    }
  }

  // Reset
  const handleReset = () => {
    setReferenceTalentIds([])
    setResults([])
    setTookMs(null)
  }

  // Table columns
  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: RecommendResultItem, index: number) => (
        <Badge
          count={index + 1}
          style={{
            backgroundColor: index < 3 ? '#faad14' : '#d9d9d9',
            color: '#fff',
          }}
        />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: RecommendResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          {name}
        </a>
      ),
    },
    {
      title: '职位',
      dataIndex: 'title',
      key: 'title',
      width: 150,
      ellipsis: true,
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 120,
      render: (score: number) => (
        <Tag color={score >= 0.7 ? 'green' : score >= 0.4 ? 'blue' : 'default'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
      sorter: (a: RecommendResultItem, b: RecommendResultItem) => a.similarity_score - b.similarity_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '推荐原因',
      dataIndex: 'reasons',
      key: 'reasons',
      render: (reasons: string[]) => (
        <List
          size="small"
          dataSource={reasons || []}
          renderItem={(item) => (
            <List.Item style={{ padding: '2px 0', border: 'none' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                • {item}
              </Text>
            </List.Item>
          )}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: RecommendResultItem) => (
        <Space>
          <Tooltip title="设为参考人才">
            <Button
              type="text"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => handleAddTalent(record.talent_id)}
              disabled={referenceTalentIds.includes(record.talent_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>
        <TeamOutlined style={{ marginRight: 8 }} />
        智能推荐
        {tookMs && (
          <Text type="secondary" style={{ fontSize: 14, marginLeft: 12, fontWeight: 'normal' }}>
            耗时 {tookMs.toFixed(0)}ms
          </Text>
        )}
      </Title>

      <Alert
        message="功能说明"
        description="选择参考人才，系统将推荐研究方向和技能相似的人才。推荐基于预计算的向量嵌入，不调用 LLM。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Reference Talents Selection */}
      <Card title="参考人才" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Space.Compact style={{ width: '100%' }}>
              <InputNumber
                placeholder="输入人才ID"
                style={{ width: 150 }}
                min={1}
                onPressEnter={(e) => {
                  const value = parseInt((e.target as HTMLInputElement).value, 10)
                  if (!isNaN(value)) {
                    handleAddTalent(value)
                  }
                }}
              />
              <Select
                showSearch
                placeholder="或搜索人才姓名..."
                style={{ width: 300 }}
                value={null}
                onSearch={handleSearchTalents}
                onChange={(value) => { if (value) handleAddTalent(value) }}
                filterOption={false}
                loading={searching}
                notFoundContent={searching ? <Spin size="small" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="搜索人才" />}
                options={talentOptions.map(t => ({
                  value: t.talent_id,
                  label: `${t.name} (${t.school_name || '未知学校'})`,
                }))}
              />
            </Space.Compact>
          </Col>
          <Col span={24}>
            <Space size={[8, 8]} wrap>
              {referenceTalentIds.map((id) => (
                <Tag
                  key={id}
                  closable
                  onClose={() => handleRemoveTalent(id)}
                  style={{ padding: '4px 8px' }}
                >
                  ID: {id}
                </Tag>
              ))}
              {referenceTalentIds.length === 0 && (
                <Text type="secondary">请添加参考人才（最多10位）</Text>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Recommendation Config */}
      <Card title="推荐配置" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 16]} align="middle">
          <Col>
            <Space>
              <Text>推荐数量:</Text>
              <InputNumber
                min={1}
                max={50}
                value={limit}
                onChange={(value) => setLimit(value ?? 10)}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<BulbOutlined />}
                onClick={handleGetRecommendations}
                loading={loading}
              >
                获取推荐
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
              >
                重置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      <Card title={`推荐结果 (${results.length} 人)`}>
        <Spin spinning={loading}>
          {results.length > 0 ? (
            <Table
              dataSource={results}
              columns={columns}
              rowKey="talent_id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 位候选人`,
              }}
            />
          ) : (
            <Empty
              description='请添加参考人才并选择推荐模式，点击"获取推荐"开始'
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default RecommendPage

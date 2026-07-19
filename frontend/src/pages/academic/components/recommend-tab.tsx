import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Select,
  Empty,
  Spin,
  Button,
  Tooltip,
  List,
  InputNumber,
  message,
  Badge,
} from 'antd'
import {
  ReloadOutlined,
  BulbOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import { semanticColors } from '../../../theme'
import type { SearchTalent, RecommendResultItem } from '../../../types'

const { Text } = Typography

interface RecommendTabProps {
  referenceTalentIds: number[]
  referenceTalentNames: Map<number, string>
  onAddReferenceTalent: (talentId: number, talentName: string) => void
  onRemoveReferenceTalent: (talentId: number) => void
  onResetReferences: () => void
}

const RecommendTab: React.FC<RecommendTabProps> = ({
  referenceTalentIds,
  referenceTalentNames,
  onAddReferenceTalent,
  onRemoveReferenceTalent,
  onResetReferences,
}) => {
  const navigate = useNavigate()

  const [recommendLimit, setRecommendLimit] = useState(10)
  const [recommendLoading, setRecommendLoading] = useState(false)
  const [talentOptions, setTalentOptions] = useState<SearchTalent[]>([])
  const [searchingTalents, setSearchingTalents] = useState(false)
  const [recommendResults, setRecommendResults] = useState<RecommendResultItem[]>([])
  const [recommendTookMs, setRecommendTookMs] = useState<number | null>(null)

  const handleSearchTalents = async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setTalentOptions([])
      return
    }
    setSearchingTalents(true)
    try {
      const response = await api.talents.list({ keyword: searchQuery, page_size: 10 })
      setTalentOptions(response.data.items || [])
    } catch {
      message.error('搜索人才失败，请稍后重试')
    } finally {
      setSearchingTalents(false)
    }
  }

  const handleGetRecommendations = async () => {
    if (referenceTalentIds.length === 0) {
      message.warning('请至少添加一位参考人才')
      return
    }
    setRecommendLoading(true)
    try {
      const response = await api.recommend.getRecommendations({
        reference_talent_ids: referenceTalentIds,
        limit: recommendLimit,
      })
      setRecommendResults(response.data.items || [])
      setRecommendTookMs(response.data.took_ms)
      message.success(`找到 ${response.data.total} 位推荐候选人`)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '获取推荐失败')
    } finally {
      setRecommendLoading(false)
    }
  }

  const handleResetRecommend = () => {
    onResetReferences()
    setRecommendResults([])
    setRecommendTookMs(null)
  }

  const recommendColumns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: RecommendResultItem, index: number) => (
        <Badge count={index + 1} style={{ backgroundColor: index < 3 ? 'var(--domain-secondary)' : semanticColors.borderGray, color: '#fff' }} />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: RecommendResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    { title: '职位', dataIndex: 'title', key: 'title', width: 150, ellipsis: true },
    {
      title: '院校机构',
      key: 'school',
      width: 150,
      ellipsis: true,
      render: (_: unknown, record: RecommendResultItem) => {
        if (record.education_school_name) {
          return (
            <span>
              {record.education_school_name}
              {record.company_school_name && record.company_school_name !== record.education_school_name && (
                <><br /><Text type="secondary" style={{ fontSize: 12 }}>{record.company_school_name}</Text></>
              )}
            </span>
          )
        }
        if (record.company_school_name) {
          return <span>{record.company_school_name}</span>
        }
        return <Text type="secondary">{record.school_name || '-'}</Text>
      },
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 120,
      render: (score: number) => <Tag color={score >= 0.7 ? 'green' : score >= 0.4 ? 'blue' : 'default'}>{(score * 100).toFixed(0)}%</Tag>,
      sorter: (a: RecommendResultItem, b: RecommendResultItem) => a.similarity_score - b.similarity_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '推荐原因',
      dataIndex: 'reasons',
      key: 'reasons',
      render: (reasons: string[]) => (
        <List size="small" dataSource={reasons || []} renderItem={(item) => <List.Item style={{ padding: '2px 0', border: 'none' }}><Text type="secondary" style={{ fontSize: 12 }}>• {item}</Text></List.Item>} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: RecommendResultItem) => (
        <Tooltip title="设为参考人才">
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => onAddReferenceTalent(record.talent_id, record.name)} disabled={referenceTalentIds.includes(record.talent_id)} />
        </Tooltip>
      ),
    },
  ]

  return (
    <>
      <Card title="参考人才" style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Select
            showSearch
            placeholder="搜索人才姓名添加参考..."
            style={{ width: '100%' }}
            size="large"
            value={null}
            onSearch={handleSearchTalents}
            onChange={(value, option) => {
              if (value && option && !Array.isArray(option)) {
                const label = typeof option.label === 'string' ? option.label : ''
                const name = label.split(' (')[0]
                onAddReferenceTalent(value as number, name)
                setTalentOptions([])
              }
            }}
            filterOption={false}
            loading={searchingTalents}
            notFoundContent={searchingTalents ? <Spin size="small" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="输入姓名搜索人才" />}
            options={talentOptions.map(t => ({ value: t.talent_id, label: `${t.name} (${t.school_name || '未知院校机构'})` }))}
          />
          <Space size={[8, 8]} wrap>
            {referenceTalentIds.map((id) => (
              <Tag key={id} closable onClose={() => onRemoveReferenceTalent(id)} style={{ padding: '4px 8px' }}>
                {referenceTalentNames.get(id) || `ID: ${id}`}
              </Tag>
            ))}
            {referenceTalentIds.length === 0 && <Text type="secondary">请在上方搜索框输入姓名添加参考人才（最多10位）</Text>}
          </Space>
        </Space>
      </Card>
      <Card title="推荐配置" style={{ marginBottom: 16 }}>
        <Space size="large">
          <Space>
            <Text>推荐数量:</Text>
            <InputNumber min={1} max={50} value={recommendLimit} onChange={(value) => setRecommendLimit(value ?? 10)} />
          </Space>
          <Space>
            <Button type="primary" icon={<BulbOutlined />} onClick={handleGetRecommendations} loading={recommendLoading}>获取推荐 {recommendTookMs && <Text type="secondary">({recommendTookMs.toFixed(0)}ms)</Text>}</Button>
            <Button icon={<ReloadOutlined />} onClick={handleResetRecommend}>重置</Button>
          </Space>
        </Space>
      </Card>
      <Card title={`推荐结果 (${recommendResults.length} 人)`}>
        <Spin spinning={recommendLoading}>
          {recommendResults.length > 0 ? (
            <Table dataSource={recommendResults} columns={recommendColumns} rowKey="talent_id" pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 位候选人` }} />
          ) : (
            <Empty description='请添加参考人才并点击"获取推荐"开始' image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>
    </>
  )
}

export default RecommendTab

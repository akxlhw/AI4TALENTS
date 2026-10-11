import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
import '../../../i18n/namespaces/academic'
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
  const { t } = useTranslation('academic')

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
      message.error(t('recommend.searchError'))
    } finally {
      setSearchingTalents(false)
    }
  }

  const handleGetRecommendations = async () => {
    if (referenceTalentIds.length === 0) {
      message.warning(t('recommend.addReferenceFirst'))
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
      message.success(t('recommend.found', { n: response.data.total }))
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || t('recommend.getError'))
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
      title: t('columns.rank'),
      key: 'rank',
      width: 60,
      render: (_: unknown, __: RecommendResultItem, index: number) => (
        <Badge count={index + 1} style={{ backgroundColor: index < 3 ? 'var(--domain-secondary)' : semanticColors.borderGray, color: '#fff' }} />
      ),
    },
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: RecommendResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    { title: t('columns.position'), dataIndex: 'title', key: 'title', width: 150, ellipsis: true },
    {
      title: t('columns.school'),
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
      title: t('columns.similarity'),
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 120,
      render: (score: number) => <Tag color={score >= 0.7 ? 'green' : score >= 0.4 ? 'blue' : 'default'}>{(score * 100).toFixed(0)}%</Tag>,
      sorter: (a: RecommendResultItem, b: RecommendResultItem) => a.similarity_score - b.similarity_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: t('columns.recommendReasons'),
      dataIndex: 'reasons',
      key: 'reasons',
      render: (reasons: string[]) => (
        <List size="small" dataSource={reasons || []} renderItem={(item) => <List.Item style={{ padding: '2px 0', border: 'none' }}><Text type="secondary" style={{ fontSize: 12 }}>• {item}</Text></List.Item>} />
      ),
    },
    {
      title: t('columns.actions'),
      key: 'actions',
      width: 100,
      render: (_: unknown, record: RecommendResultItem) => (
        <Tooltip title={t('recommend.setReferenceTip')}>
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => onAddReferenceTalent(record.talent_id, record.name)} disabled={referenceTalentIds.includes(record.talent_id)} />
        </Tooltip>
      ),
    },
  ]

  return (
    <>
      <Card title={t('recommend.referenceTitle')} style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Select
            showSearch
            placeholder={t('recommend.referencePlaceholder')}
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
            notFoundContent={searchingTalents ? <Spin size="small" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('recommend.referenceSearchHint')} />}
            options={talentOptions.map(item => ({ value: item.talent_id, label: `${item.name} (${item.school_name || t('recommend.unknownSchool')})` }))}
          />
          <Space size={[8, 8]} wrap>
            {referenceTalentIds.map((id) => (
              <Tag key={id} closable onClose={() => onRemoveReferenceTalent(id)} style={{ padding: '4px 8px' }}>
                {referenceTalentNames.get(id) || `ID: ${id}`}
              </Tag>
            ))}
            {referenceTalentIds.length === 0 && <Text type="secondary">{t('recommend.referenceHint')}</Text>}
          </Space>
        </Space>
      </Card>
      <Card title={t('recommend.configTitle')} style={{ marginBottom: 16 }}>
        <Space size="large">
          <Space>
            <Text>{t('recommend.limitLabel')}</Text>
            <InputNumber min={1} max={50} value={recommendLimit} onChange={(value) => setRecommendLimit(value ?? 10)} />
          </Space>
          <Space>
            <Button type="primary" icon={<BulbOutlined />} onClick={handleGetRecommendations} loading={recommendLoading}>{t('recommend.getAction')} {recommendTookMs && <Text type="secondary">({recommendTookMs.toFixed(0)}ms)</Text>}</Button>
            <Button icon={<ReloadOutlined />} onClick={handleResetRecommend}>{t('recommend.reset')}</Button>
          </Space>
        </Space>
      </Card>
      <Card title={t('recommend.resultsTitle', { n: recommendResults.length })}>
        <Spin spinning={recommendLoading}>
          {recommendResults.length > 0 ? (
            <Table dataSource={recommendResults} columns={recommendColumns} rowKey="talent_id" pagination={{ pageSize: 10, showTotal: (count) => t('recommend.candidatesTotal', { n: count }) }} />
          ) : (
            <Empty description={t('recommend.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Spin>
      </Card>
    </>
  )
}

export default RecommendTab

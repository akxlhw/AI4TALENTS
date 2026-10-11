import { useCallback, useEffect, useState } from 'react'
import { Modal, Table, Tag, Spin, message, Typography, Space } from 'antd'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { getRoleTypeConfig, LEGACY_ROLE_TYPE_MAP } from '../constants/roleType'
import '../i18n/namespaces/academic'

const { Text } = Typography

interface TalentCompareData {
  talent_id: number
  name: string
  name_en: string | null
  orcid: string | null
  role_type: string
  school_name: string | null
  current_title: string | null
  department_name: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  latest_active_year: number | null
  topic_tags: string[]
  academic_age: number | null
}

interface CompareResponse {
  talents: TalentCompareData[]
  comparison_fields: { key: string; label: string }[]
}

interface TalentCompareModalProps {
  visible: boolean
  talentIds: number[]
  onClose: () => void
}

const TalentCompareModal: React.FC<TalentCompareModalProps> = ({
  visible,
  talentIds,
  onClose,
}) => {
  const { t } = useTranslation(['common', 'academic'])
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CompareResponse | null>(null)

  const fetchCompareData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.talents.compare(talentIds)
      setData(response.data)
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || t('compare.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [talentIds, t])

  useEffect(() => {
    if (visible && talentIds.length >= 2 && talentIds.length <= 4) {
      fetchCompareData()
    }
  }, [visible, talentIds, fetchCompareData])

  const renderValue = (key: string, talent: TalentCompareData) => {
    switch (key) {
      case 'name':
        return (
          <Space direction="vertical" size={0}>
            <Text strong>{talent.name}</Text>
            {talent.name_en && (
              <Text type="secondary" style={{ fontSize: 12 }}>{talent.name_en}</Text>
            )}
          </Space>
        )
      case 'role_type': {
        const config = getRoleTypeConfig(talent.role_type)
        const normalized = LEGACY_ROLE_TYPE_MAP[talent.role_type] ?? talent.role_type
        return (
          <Tag color={config.color}>
            {t(`roles.${normalized}`, { defaultValue: config.text })}
          </Tag>
        )
      }
      case 'topic_tags':
        return (
          <Space size={4} wrap>
            {(talent.topic_tags || []).slice(0, 3).map(tag => (
              <Tag key={tag} style={{ margin: 0, fontSize: 11 }}>{tag}</Tag>
            ))}
            {talent.topic_tags && talent.topic_tags.length > 3 && (
              <Text type="secondary" style={{ fontSize: 11 }}>+{talent.topic_tags.length - 3}</Text>
            )}
          </Space>
        )
      case 'cited_by_count':
        return talent[key]?.toLocaleString() || '-'
      default:
        const value = (talent as unknown as Record<string, unknown>)[key]
        return value ?? '-'
    }
  }

  const columns = [
    {
      title: t('compare.field'),
      dataIndex: 'label',
      key: 'label',
      width: 120,
      fixed: 'left' as const,
    },
    ...(data?.talents || []).map((tal) => ({
      title: tal.name,
      dataIndex: `talent_${tal.talent_id}`,
      key: `talent_${tal.talent_id}`,
      width: 200,
      render: (_: unknown, record: { key: string; label: string }) => renderValue(record.key, tal),
    })),
  ]

  const tableData = (data?.comparison_fields || []).map(field => {
    const row: { key: string; label: string; [k: string]: unknown } = { key: field.key, label: field.label }
    data?.talents.forEach(tal => {
      row[`talent_${tal.talent_id}`] = (tal as unknown as Record<string, unknown>)[field.key]
    })
    return row
  })

  return (
    <Modal
      title={t('compare.title')}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={900}
    >
      <Spin spinning={loading}>
        {data && (
          <Table
            dataSource={tableData}
            columns={columns}
            rowKey="key"
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        )}
        {!loading && !data && (
          <Text type="secondary">{t('compare.selectHint')}</Text>
        )}
      </Spin>
    </Modal>
  )
}

export default TalentCompareModal

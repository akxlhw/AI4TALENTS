import { useEffect, useState } from 'react'
import { Modal, Table, Tag, Spin, message, Typography, Space } from 'antd'
import { api } from '../services/api'

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

const roleTypeMap: Record<string, { color: string; text: string }> = {
  professor: { color: 'green', text: '教授' },
  student: { color: 'blue', text: '学生' },
  graduated: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
}

const TalentCompareModal: React.FC<TalentCompareModalProps> = ({
  visible,
  talentIds,
  onClose,
}) => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CompareResponse | null>(null)

  useEffect(() => {
    if (visible && talentIds.length >= 2 && talentIds.length <= 4) {
      fetchCompareData()
    }
  }, [visible, talentIds])

  const fetchCompareData = async () => {
    setLoading(true)
    try {
      const response = await api.talents.compare(talentIds)
      setData(response.data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取对比数据失败')
    } finally {
      setLoading(false)
    }
  }

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
      case 'role_type':
        const config = roleTypeMap[talent.role_type] || roleTypeMap.unknown
        return <Tag color={config.color}>{config.text}</Tag>
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
        const value = (talent as any)[key]
        return value ?? '-'
    }
  }

  const columns = [
    {
      title: '对比项',
      dataIndex: 'label',
      key: 'label',
      width: 120,
      fixed: 'left' as const,
    },
    ...(data?.talents || []).map((t, idx) => ({
      title: t.name,
      dataIndex: `talent_${t.talent_id}`,
      key: `talent_${t.talent_id}`,
      width: 200,
      render: (_: any, record: any) => renderValue(record.key, t),
    })),
  ]

  const tableData = (data?.comparison_fields || []).map(field => {
    const row: any = { key: field.key, label: field.label }
    data?.talents.forEach(t => {
      row[`talent_${t.talent_id}`] = (t as any)[field.key]
    })
    return row
  })

  return (
    <Modal
      title="候选人对比"
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
          <Text type="secondary">请选择2-4位候选人进行对比</Text>
        )}
      </Spin>
    </Modal>
  )
}

export default TalentCompareModal

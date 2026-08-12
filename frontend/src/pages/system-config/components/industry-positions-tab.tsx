import { useMemo, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { BuildOutlined, PlusOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../../services/api'
import type { IndustryPosition, IndustryPositionPayload } from '../../../services/api/industry'
import { useIndustryPositions, useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import { queryKeys } from '../../../hooks/queryClient'
import { getErrorMessage } from '../../../utils'
import {
  POSITION_STATUS_COLORS,
  POSITION_STATUS_LABELS,
  formatScore,
} from '../../../pages/industry/constants/industry-config'

const { Text, Title } = Typography

interface PositionFormValues {
  title: string
  department?: string
  tech_direction_codes: string[]
  level_min?: number | null
  level_max?: number | null
  jd_text?: string
  status: string
}

const STATUS_OPTIONS = Object.entries(POSITION_STATUS_LABELS).map(([value, label]) => ({
  value,
  label,
}))

/**
 * Industry position management tab (super_admin, system-config).
 * CRUD without physical delete — lifecycle via status (open/closed/archived).
 */
const IndustryPositionsTab: React.FC = () => {
  const queryClient = useQueryClient()
  const { data: positions, isLoading } = useIndustryPositions()
  const { data: directions } = useTechDirectionOptions()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<IndustryPosition | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<PositionFormValues>()

  const directionName = useMemo(() => {
    const map = new Map<string, string>()
    ;(directions || []).forEach(d => map.set(d.code, d.name))
    return (code: string) => map.get(code) || code
  }, [directions])

  // Group direction options by tech domain for the multi-select
  const directionOptions = useMemo(() => {
    const groups = new Map<string, { value: string; label: string }[]>()
    ;(directions || []).forEach(d => {
      const list = groups.get(d.domainName) || []
      list.push({ value: d.code, label: d.name })
      groups.set(d.domainName, list)
    })
    return Array.from(groups.entries()).map(([label, options]) => ({ label, options }))
  }, [directions])

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.industry.positions() })

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'open', tech_direction_codes: [] })
    setModalOpen(true)
  }

  const openEdit = (p: IndustryPosition) => {
    setEditing(p)
    form.setFieldsValue({
      title: p.title,
      department: p.department || undefined,
      tech_direction_codes: p.tech_direction_codes || [],
      level_min: p.level_min,
      level_max: p.level_max,
      jd_text: p.jd_text || undefined,
      status: p.status,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    if (
      values.level_min != null &&
      values.level_max != null &&
      values.level_min > values.level_max
    ) {
      message.error('职级下限不能大于上限')
      return
    }
    const payload: IndustryPositionPayload = {
      title: values.title,
      department: values.department || null,
      tech_direction_codes: values.tech_direction_codes || [],
      level_min: values.level_min ?? null,
      level_max: values.level_max ?? null,
      jd_text: values.jd_text || null,
      status: values.status,
    }
    setSaving(true)
    try {
      if (editing) {
        await api.industry.updatePosition(editing.position_id, payload)
        message.success('岗位已更新')
      } else {
        await api.industry.createPosition(payload)
        message.success('岗位已创建')
      }
      setModalOpen(false)
      invalidate()
    } catch (e) {
      message.error(getErrorMessage(e, '保存失败'))
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (p: IndustryPosition, status: string) => {
    try {
      await api.industry.updatePosition(p.position_id, { status })
      message.success(`「${p.title}」已切换为${POSITION_STATUS_LABELS[status] || status}`)
      invalidate()
    } catch (e) {
      message.error(getErrorMessage(e, '状态切换失败'))
    }
  }

  const columns: ColumnsType<IndustryPosition> = [
    {
      title: '岗位名称',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, p) => (
        <div>
          <Text strong>{title}</Text>
          {p.status === 'archived' && (
            <Tag style={{ marginLeft: 8 }} color="default">
              已归档
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (v: string | null) => v || '—',
    },
    {
      title: '技术方向',
      dataIndex: 'tech_direction_codes',
      key: 'tech_direction_codes',
      render: (codes: string[]) =>
        codes && codes.length > 0 ? (
          <Space size={4} wrap>
            {codes.map(c => (
              <Tag
                key={c}
                style={{
                  margin: 0,
                  borderRadius: 8,
                  border: 'none',
                  background: 'var(--domain-light-bg, #FAF5FF)',
                  color: 'var(--domain-badge-bg, #6B46C1)',
                  fontSize: 11,
                }}
              >
                {directionName(c)}
              </Tag>
            ))}
          </Space>
        ) : (
          '—'
        ),
    },
    {
      title: '职级',
      key: 'level',
      width: 90,
      render: (_, p) =>
        p.level_min != null || p.level_max != null
          ? `${p.level_min ?? '?'} - ${p.level_max ?? '?'}`
          : '—',
    },
    {
      title: '候选人数',
      dataIndex: 'candidate_count',
      key: 'candidate_count',
      width: 90,
      align: 'right',
    },
    {
      title: '平均匹配分',
      dataIndex: 'avg_match_score',
      key: 'avg_match_score',
      width: 100,
      align: 'right',
      render: (v: number | null) => (v != null ? formatScore(v) : '—'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: string, p) => (
        <Select
          size="small"
          value={status}
          options={STATUS_OPTIONS}
          onChange={v => handleStatusChange(p, v)}
          style={{ width: 110 }}
          labelRender={props => (
            <Tag
              color={POSITION_STATUS_COLORS[props.value as string] || 'default'}
              style={{ margin: 0, borderRadius: 8 }}
            >
              {props.label}
            </Tag>
          )}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, p) => (
        <Button type="link" size="small" onClick={() => openEdit(p)}>
          编辑
        </Button>
      ),
    },
  ]

  return (
    <Card>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <Title level={5} style={{ margin: 0 }}>
            <BuildOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
            行业人才岗位
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            岗位不提供物理删除，通过状态流转（在招 → 已关闭 → 已归档）管理生命周期
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建岗位
        </Button>
      </div>

      <Table<IndustryPosition>
        rowKey="position_id"
        loading={isLoading}
        columns={columns}
        dataSource={positions || []}
        pagination={false}
        locale={{ emptyText: '暂无岗位，点击右上角「新建岗位」开始' }}
      />

      <Modal
        title={editing ? '编辑岗位' : '新建岗位'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={560}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="title"
            label="岗位名称"
            rules={[{ required: true, message: '请输入岗位名称' }]}
          >
            <Input placeholder="如：大模型推理工程师" maxLength={255} />
          </Form.Item>
          <Form.Item name="department" label="所属部门">
            <Input placeholder="如：云平台事业部" maxLength={255} />
          </Form.Item>
          <Form.Item name="tech_direction_codes" label="技术方向（可多选或手动输入）">
            <Select
              mode="tags"
              placeholder="选择预设方向，或直接输入自定义方向后回车"
              options={directionOptions}
              optionFilterProp="label"
              showSearch
              allowClear
            />
          </Form.Item>
          <Space size={16} style={{ display: 'flex' }}>
            <Form.Item name="level_min" label="职级下限" style={{ flex: 1 }}>
              <InputNumber placeholder="如 19" min={1} max={99} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="level_max" label="职级上限" style={{ flex: 1 }}>
              <InputNumber placeholder="如 20" min={1} max={99} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="status" label="状态" style={{ flex: 1 }}>
              <Select options={STATUS_OPTIONS} />
            </Form.Item>
          </Space>
          <Form.Item name="jd_text" label="JD 原文">
            <Input.TextArea rows={5} placeholder="粘贴岗位 JD 原文（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

export default IndustryPositionsTab

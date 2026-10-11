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
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../../services/api'
import type { IndustryPosition, IndustryPositionPayload } from '../../../services/api/industry'
import { useIndustryPositions, useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import { queryKeys } from '../../../hooks/queryClient'
import { getErrorMessage } from '../../../utils'
import '../../../i18n/namespaces/system-config'
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

/**
 * Industry position management tab (super_admin, system-config).
 * CRUD without physical delete — lifecycle via status (open/closed/archived).
 */
const IndustryPositionsTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const queryClient = useQueryClient()
  const { data: positions, isLoading } = useIndustryPositions()
  const { data: directions } = useTechDirectionOptions()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<IndustryPosition | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<PositionFormValues>()

  const statusLabel = (status: string) =>
    t(`industryPositions.positionStatus.${status}`, {
      defaultValue: POSITION_STATUS_LABELS[status] || status,
    })

  const statusOptions = useMemo(
    () =>
      Object.entries(POSITION_STATUS_LABELS).map(([value, fallback]) => ({
        value,
        label: t(`industryPositions.positionStatus.${value}`, { defaultValue: fallback }),
      })),
    [t]
  )

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
      message.error(t('industryPositions.levelRangeError'))
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
        message.success(t('industryPositions.positionUpdated'))
      } else {
        await api.industry.createPosition(payload)
        message.success(t('industryPositions.positionCreated'))
      }
      setModalOpen(false)
      invalidate()
    } catch (e) {
      message.error(getErrorMessage(e, t('common.saveFailed')))
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (p: IndustryPosition, status: string) => {
    try {
      await api.industry.updatePosition(p.position_id, { status })
      message.success(
        t('industryPositions.statusChanged', { title: p.title, status: statusLabel(status) })
      )
      invalidate()
    } catch (e) {
      message.error(getErrorMessage(e, t('industryPositions.statusChangeFailed')))
    }
  }

  const columns: ColumnsType<IndustryPosition> = [
    {
      title: t('industryPositions.columns.title'),
      dataIndex: 'title',
      key: 'title',
      render: (title: string, p) => (
        <div>
          <Text strong>{title}</Text>
          {p.status === 'archived' && (
            <Tag style={{ marginLeft: 8 }} color="default">
              {t('industryPositions.archivedTag')}
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: t('industryPositions.columns.department'),
      dataIndex: 'department',
      key: 'department',
      render: (v: string | null) => v || '—',
    },
    {
      title: t('industryPositions.columns.techDirection'),
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
      title: t('industryPositions.columns.level'),
      key: 'level',
      width: 90,
      render: (_, p) =>
        p.level_min != null || p.level_max != null
          ? `${p.level_min ?? '?'} - ${p.level_max ?? '?'}`
          : '—',
    },
    {
      title: t('industryPositions.columns.candidates'),
      dataIndex: 'candidate_count',
      key: 'candidate_count',
      width: 90,
      align: 'right',
    },
    {
      title: t('industryPositions.columns.avgScore'),
      dataIndex: 'avg_match_score',
      key: 'avg_match_score',
      width: 100,
      align: 'right',
      render: (v: number | null) => (v != null ? formatScore(v) : '—'),
    },
    {
      title: t('industryPositions.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: string, p) => (
        <Select
          size="small"
          value={status}
          options={statusOptions}
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
      title: t('industryPositions.columns.actions'),
      key: 'actions',
      width: 80,
      render: (_, p) => (
        <Button type="link" size="small" onClick={() => openEdit(p)}>
          {t('industryPositions.actions.edit')}
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
            {t('industryPositions.heading')}
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('industryPositions.headingDescription', {
              open: statusLabel('open'),
              closed: statusLabel('closed'),
              archived: statusLabel('archived'),
            })}
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t('industryPositions.createButton')}
        </Button>
      </div>

      <Table<IndustryPosition>
        rowKey="position_id"
        loading={isLoading}
        columns={columns}
        dataSource={positions || []}
        pagination={false}
        locale={{ emptyText: t('industryPositions.emptyText') }}
      />

      <Modal
        title={editing ? t('industryPositions.modal.editTitle') : t('industryPositions.modal.createTitle')}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        okText={t('industryPositions.modal.okText')}
        cancelText={t('industryPositions.modal.cancelText')}
        width={560}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="title"
            label={t('industryPositions.form.titleLabel')}
            rules={[{ required: true, message: t('industryPositions.form.titleRequired') }]}
          >
            <Input placeholder={t('industryPositions.form.titlePlaceholder')} maxLength={255} />
          </Form.Item>
          <Form.Item name="department" label={t('industryPositions.form.departmentLabel')}>
            <Input placeholder={t('industryPositions.form.departmentPlaceholder')} maxLength={255} />
          </Form.Item>
          <Form.Item name="tech_direction_codes" label={t('industryPositions.form.techDirectionLabel')}>
            <Select
              mode="tags"
              placeholder={t('industryPositions.form.techDirectionPlaceholder')}
              options={directionOptions}
              optionFilterProp="label"
              showSearch
              allowClear
            />
          </Form.Item>
          <Space size={16} style={{ display: 'flex' }}>
            <Form.Item name="level_min" label={t('industryPositions.form.levelMinLabel')} style={{ flex: 1 }}>
              <InputNumber placeholder={t('industryPositions.form.levelMinPlaceholder')} min={1} max={99} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="level_max" label={t('industryPositions.form.levelMaxLabel')} style={{ flex: 1 }}>
              <InputNumber placeholder={t('industryPositions.form.levelMaxPlaceholder')} min={1} max={99} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="status" label={t('industryPositions.form.statusLabel')} style={{ flex: 1 }}>
              <Select options={statusOptions} />
            </Form.Item>
          </Space>
          <Form.Item name="jd_text" label={t('industryPositions.form.jdTextLabel')}>
            <Input.TextArea rows={5} placeholder={t('industryPositions.form.jdTextPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

export default IndustryPositionsTab

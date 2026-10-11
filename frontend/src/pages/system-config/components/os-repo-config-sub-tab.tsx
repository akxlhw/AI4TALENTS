import { useState, useEffect, useCallback, useMemo } from 'react'
import { semanticColors } from '../../../theme'
import {
  Card,
  Collapse,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  message,
  Popconfirm,
  Empty,
  Spin,
  Row,
  Col,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  DatabaseOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  GithubOutlined,
  PlayCircleOutlined,
  ClearOutlined,
  TagsOutlined,
  RadarChartOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { api } from '../../../services/api'
import type { OSPurgePreview, OSRepoConfig } from '../../../types'
import { getErrorMessage } from './utils'

const { Text } = Typography

// Taxonomy v2: 34 element codes grouped by 10 domains (shared module)
import {
  TECH_ELEMENT_GROUPS,
  getTechElementColor,
  useTechElements,
} from '@/constants/tech-elements'
import '../../../i18n/namespaces/system-config'
import OsDiscoverSubTab from './os-discover-sub-tab'

const OSRepoConfigSubTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const { fullLabel } = useTechElements()
  const [data, setData] = useState<OSRepoConfig[]>([])

  // TECH_ELEMENT_GROUPS labels are i18n keys — translate for Select options
  const { t: tTax } = useTranslation('taxonomy')
  const translatedTechGroups = useMemo(
    () =>
      TECH_ELEMENT_GROUPS.map(g => ({
        label: tTax(g.label),
        options: g.options.map(o => ({ ...o, label: tTax(o.label) })),
      })),
    [tTax]
  )
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState<OSRepoConfig | null>(null)
  const [form] = Form.useForm()
  const [filterTechElement, setFilterTechElement] = useState<string[]>([])
  const [searchKeyword, setSearchKeyword] = useState('')
  const [collectingIds, setCollectingIds] = useState<Set<number>>(new Set())
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [collectRecord, setCollectRecord] = useState<OSRepoConfig | null>(null)
  const [collectHistory, setCollectHistory] = useState<{
    last_status_label: string
    last_collected_at: string
    last_records: number
  } | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [batchCollectModalVisible, setBatchCollectModalVisible] = useState(false)
  const [batchContributorsPerRepo, setBatchContributorsPerRepo] = useState<number>(0)
  const [batchHistoryModal, setBatchHistoryModal] = useState<{
    visible: boolean
    collected: {
      repo_config_id: number
      repo_full_name: string
      last_status_label: string
      last_collected_at: string
      last_records: number
    }[]
    allIds: number[]
  }>({ visible: false, collected: [], allIds: [] })
  const [purgeModalVisible, setPurgeModalVisible] = useState(false)
  const [purgeRecord, setPurgeRecord] = useState<OSRepoConfig | null>(null)
  const [purgePreview, setPurgePreview] = useState<OSPurgePreview | null>(null)
  const [purgeLoading, setPurgeLoading] = useState(false)
  const [purgeExecuting, setPurgeExecuting] = useState(false)
  const [purgeConfirmText, setPurgeConfirmText] = useState('')
  const [batchAddModalVisible, setBatchAddModalVisible] = useState(false)
  const [batchAddText, setBatchAddText] = useState('')
  const [batchAddTech, setBatchAddTech] = useState<string[]>(['ai'])
  const [batchAddLoading, setBatchAddLoading] = useState(false)
  const [batchTechModalVisible, setBatchTechModalVisible] = useState(false)
  const [batchTechValue, setBatchTechValue] = useState<string[]>([])
  const [batchTechLoading, setBatchTechLoading] = useState(false)
  const [purgeDeleteConfig, setPurgeDeleteConfig] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize }
      if (filterTechElement.length > 0) params.tech_elements = filterTechElement
      if (searchKeyword) params.q = searchKeyword
      const response = await api.openSource.listRepoConfigs(params)
      setData(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch {
      message.error(t('osRepoConfig.messages.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filterTechElement, searchKeyword, t])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleCreate = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, collect_enabled: true })
    setModalVisible(true)
  }

  const handleEdit = (record: OSRepoConfig) => {
    setEditingRecord(record)
    form.setFieldsValue({
      repo_full_name: record.repo_full_name,
      display_name: record.display_name,
      description: record.description,
      tech_element: record.tech_element,
      language: record.language,
      is_active: record.is_active,
      collect_enabled: record.collect_enabled,
      notes: record.notes,
    })
    setModalVisible(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingRecord) {
        await api.openSource.updateRepoConfig(editingRecord.repo_config_id, values)
        message.success(t('osRepoConfig.messages.updated'))
      } else {
        await api.openSource.createRepoConfig(values)
        message.success(t('osRepoConfig.messages.created'))
      }
      setModalVisible(false)
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.saveFailed')))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.openSource.deleteRepoConfig(id)
      message.success(t('osRepoConfig.messages.deleted'))
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.deleteFailed')))
    }
  }

  const handleExportSelected = () => {
    const rows = data.filter(r => selectedRowKeys.includes(r.repo_config_id))
    if (rows.length === 0) return
    const escape = (v: unknown) => {
      const s = v == null ? '' : String(v)
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
    }
    const header = [
      t('osRepoConfig.csv.repoFullName'),
      t('osRepoConfig.csv.displayName'),
      t('osRepoConfig.csv.techDomain'),
      t('osRepoConfig.csv.language'),
      t('osRepoConfig.csv.stars'),
      t('osRepoConfig.csv.activeDisplay'),
      t('osRepoConfig.csv.collectEnabled'),
      t('osRepoConfig.csv.description'),
      t('osRepoConfig.csv.notes'),
    ]
    const lines = rows.map(r =>
      [
        r.repo_full_name,
        r.display_name || '',
        (Array.isArray(r.tech_element) ? r.tech_element : [r.tech_element])
          .map(c => fullLabel(c))
          .join(' | '),
        r.language || '',
        r.stars_count ?? 0,
        r.is_active ? t('osRepoConfig.yes') : t('osRepoConfig.no'),
        r.collect_enabled ? t('osRepoConfig.yes') : t('osRepoConfig.no'),
        r.description || '',
        r.notes || '',
      ]
        .map(escape)
        .join(',')
    )
    const csv = '﻿' + [header.map(escape).join(','), ...lines].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = t('osRepoConfig.csv.filename', {
      date: new Date().toISOString().slice(0, 10),
    })
    a.click()
    window.URL.revokeObjectURL(url)
    message.success(t('osRepoConfig.messages.exported', { n: rows.length }))
  }

  const handleCollect = async (record: OSRepoConfig) => {
    setCollectRecord(record)
    setCollectHistory(null)
    try {
      const res = await api.openSource.checkCollectionHistory([record.repo_config_id])
      if (res.data && res.data.length > 0) {
        setCollectHistory(res.data[0])
      }
    } catch {
      // ignore — proceed without history check
    }
    setCollectModalVisible(true)
  }

  const handlePurge = async (record: OSRepoConfig) => {
    setPurgeRecord(record)
    setPurgePreview(null)
    setPurgeConfirmText('')
    setPurgeDeleteConfig(false)
    setPurgeModalVisible(true)
    setPurgeLoading(true)
    try {
      const response = await api.openSource.purgeRepoConfigData(record.repo_config_id, {
        dry_run: true,
      })
      setPurgePreview(response.data)
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.purgePreviewFailed')))
      setPurgeModalVisible(false)
    } finally {
      setPurgeLoading(false)
    }
  }

  const handleConfirmPurge = async () => {
    if (!purgeRecord) return
    setPurgeExecuting(true)
    try {
      const response = await api.openSource.purgeRepoConfigData(purgeRecord.repo_config_id, {
        dry_run: false,
        delete_config: purgeDeleteConfig,
      })
      const result: OSPurgePreview = response.data
      message.success(
        t('osRepoConfig.purge.done', {
          repo: result.repo_full_name,
          contributions: result.contributions,
          developers: result.developers_exclusive,
          configDeleted: result.config_deleted ? t('osRepoConfig.purge.configDeleted') : '',
        })
      )
      setPurgeModalVisible(false)
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.purge.failed')))
    } finally {
      setPurgeExecuting(false)
    }
  }

  const handleBatchAdd = async () => {
    const lines = batchAddText
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean)
    if (lines.length === 0) {
      message.warning(t('osRepoConfig.messages.batchAddEmpty'))
      return
    }
    setBatchAddLoading(true)
    try {
      const res = await api.openSource.batchCreateRepoConfigs({
        repo_inputs: lines,
        tech_element: batchAddTech,
      })
      const { created, skipped, failed } = res.data
      setBatchAddModalVisible(false)
      setBatchAddText('')

      const parts: React.ReactNode[] = []
      if (created.length > 0) {
        parts.push(
          <div key="created" style={{ marginBottom: 12 }}>
            <Text strong style={{ color: '#52c41a' }}>
              {t('osRepoConfig.batchAdd.created', { n: created.length })}
            </Text>
            {created.map(
              (c: { repo_full_name: string; language?: string; stars_count?: number }) => (
                <div key={c.repo_full_name} style={{ fontSize: 12, marginLeft: 16, marginTop: 2 }}>
                  • {c.repo_full_name}
                  {c.language && ` (${c.language}`}
                  {c.stars_count != null &&
                    c.stars_count > 0 &&
                    `, ${c.stars_count >= 1000 ? `${(c.stars_count / 1000).toFixed(1)}k` : c.stars_count} stars`}
                  {c.language && ')'}
                </div>
              )
            )}
          </div>
        )
      }
      if (skipped.length > 0) {
        parts.push(
          <div key="skipped" style={{ marginBottom: 12 }}>
            <Text strong style={{ color: '#faad14' }}>
              {t('osRepoConfig.batchAdd.skipped', { n: skipped.length })}
            </Text>
            {skipped.map((s: { repo_input: string; reason: string }, i: number) => (
              <div key={i} style={{ fontSize: 12, marginLeft: 16, marginTop: 2 }}>
                • {s.repo_input}: {s.reason}
              </div>
            ))}
          </div>
        )
      }
      if (failed.length > 0) {
        parts.push(
          <div key="failed">
            <Text strong style={{ color: '#ff4d4f' }}>
              {t('osRepoConfig.batchAdd.failed', { n: failed.length })}
            </Text>
            {failed.map((f: { repo_input: string; reason: string }, i: number) => (
              <div key={i} style={{ fontSize: 12, marginLeft: 16, marginTop: 2 }}>
                • {f.repo_input}: {f.reason}
              </div>
            ))}
          </div>
        )
      }
      if (parts.length > 0) {
        Modal.info({
          title: t('osRepoConfig.batchAdd.resultTitle'),
          width: 520,
          content: <div style={{ maxHeight: 400, overflow: 'auto' }}>{parts}</div>,
        })
      }
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.batchAddFailed')))
    } finally {
      setBatchAddLoading(false)
    }
  }

  const handleBatchTechUpdate = async () => {
    if (batchTechValue.length === 0) {
      message.warning(t('osRepoConfig.messages.techEmpty'))
      return
    }
    const ids = selectedRowKeys.map(k => Number(k))
    if (ids.length === 0) return
    setBatchTechLoading(true)
    try {
      const res = await api.openSource.batchUpdateTechElement({
        repo_config_ids: ids,
        tech_element: batchTechValue,
      })
      setBatchTechModalVisible(false)
      const { updated, failed } = res.data
      if (updated > 0) {
        message.success(t('osRepoConfig.messages.techUpdated', { n: updated }))
      }
      if (failed.length > 0) {
        Modal.warning({
          title: t('osRepoConfig.batchTech.updateFailedTitle', { n: failed.length }),
          content: (
            <div style={{ maxHeight: 240, overflow: 'auto' }}>
              {failed.map((f: { repo_input: string; reason: string }, i: number) => (
                <div key={i} style={{ marginBottom: 4, fontSize: 12 }}>
                  • #{f.repo_input}: {f.reason}
                </div>
              ))}
            </div>
          ),
        })
      }
      setSelectedRowKeys([])
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.techUpdateFailed')))
    } finally {
      setBatchTechLoading(false)
    }
  }

  const handleConfirmCollect = async () => {
    if (!collectRecord) return
    try {
      setCollectModalVisible(false)
      setCollectingIds(prev => new Set(prev).add(collectRecord.repo_config_id))
      await api.openSource.collectRepo(collectRecord.repo_config_id)
      message.success(
        t('osRepoConfig.messages.collectStarted', { repo: collectRecord.repo_full_name })
      )
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.collectStartFailed')))
    } finally {
      setCollectingIds(prev => {
        const next = new Set(prev)
        next.delete(collectRecord.repo_config_id)
        return next
      })
    }
  }

  const handleBatchCollect = async () => {
    if (selectedRowKeys.length === 0) return
    const ids = selectedRowKeys.map(k => Number(k))
    try {
      const res = await api.openSource.checkCollectionHistory(ids)
      const collected = res.data || []
      if (collected.length > 0) {
        // Some repos already collected — show 3-choice modal
        setBatchHistoryModal({ visible: true, collected, allIds: ids })
      } else {
        // No history — go straight to normal batch modal
        setBatchCollectModalVisible(true)
      }
    } catch {
      // Check failed — proceed without warning
      setBatchCollectModalVisible(true)
    }
  }

  const executeBatchCollect = async (ids: number[]) => {
    try {
      ids.forEach(id => {
        setCollectingIds(prev => new Set(prev).add(id))
      })
      const response = await api.openSource.collectBatchRepos(ids, batchContributorsPerRepo)
      const { created, skipped } = response.data
      if (created.length > 0) {
        message.success(t('osRepoConfig.messages.batchCollectStarted', { n: created.length }))
      }
      if (skipped.length > 0) {
        const reasons = skipped.map(
          (s: { repo_full_name?: string; reason: string }) =>
            `${s.repo_full_name || t('osRepoConfig.messages.unknownRepo')}: ${s.reason}`
        )
        Modal.warning({
          title: t('osRepoConfig.batchCollect.skippedTitle', { n: skipped.length }),
          content: (
            <div style={{ maxHeight: 240, overflow: 'auto' }}>
              {reasons.map((r: string, i: number) => (
                <div key={i} style={{ marginBottom: 4 }}>
                  {r}
                </div>
              ))}
            </div>
          ),
        })
      }
      if (created.length === 0 && skipped.length === 0) {
        message.info(t('osRepoConfig.messages.batchCollectNoneStarted'))
      }
      setSelectedRowKeys([])
    } catch (error) {
      message.error(getErrorMessage(error, t('osRepoConfig.messages.batchCollectStartFailed')))
    } finally {
      ids.forEach(id => {
        setCollectingIds(prev => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
      })
    }
  }

  const handleConfirmBatchCollect = async () => {
    setBatchCollectModalVisible(false)
    const ids = selectedRowKeys.map(k => Number(k))
    await executeBatchCollect(ids)
  }

  const columns = [
    {
      title: t('osRepoConfig.columns.displayName'),
      dataIndex: 'display_name',
      key: 'display_name',
      render: (name: string, record: OSRepoConfig) => (
        <Space>
          <GithubOutlined />
          <Text strong>{name || record.repo_full_name}</Text>
        </Space>
      ),
    },
    {
      title: t('osRepoConfig.columns.repoFullName'),
      dataIndex: 'repo_full_name',
      key: 'repo_full_name',
      render: (name: string) => (
        <a href={`https://github.com/${name}`} target="_blank" rel="noopener noreferrer">
          {name}
        </a>
      ),
    },
    {
      title: t('osRepoConfig.columns.techElement'),
      dataIndex: 'tech_element',
      key: 'tech_element',
      width: 200,
      render: (codes: string[] | string) => {
        const list = Array.isArray(codes) ? codes : [codes]
        return (
          <Space size={2} wrap>
            {list.map(code => (
              <Tag key={code} color={getTechElementColor(code)} style={{ margin: 0 }}>
                {fullLabel(code)}
              </Tag>
            ))}
          </Space>
        )
      },
    },

    {
      title: t('osRepoConfig.columns.actions'),
      key: 'actions',
      width: 150,
      render: (_: unknown, record: OSRepoConfig) => (
        <Space>
          <Tooltip title={t('osRepoConfig.tooltips.startCollect')}>
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleCollect(record)}
              loading={collectingIds.has(record.repo_config_id)}
              disabled={!record.collect_enabled || collectingIds.has(record.repo_config_id)}
            >
              {t('osRepoConfig.actions.collect')}
            </Button>
          </Tooltip>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('osRepoConfig.actions.edit')}
          </Button>
          <Popconfirm
            title={t('osRepoConfig.deleteConfirm')}
            onConfirm={() => handleDelete(record.repo_config_id)}
            okText={t('common:actions.confirm')}
            cancelText={t('common:actions.cancel')}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              {t('common:actions.delete')}
            </Button>
          </Popconfirm>
          <Tooltip title={t('osRepoConfig.tooltips.purge')}>
            <Button
              type="link"
              size="small"
              danger
              icon={<ClearOutlined />}
              onClick={() => handlePurge(record)}
            >
              {t('osRepoConfig.actions.purge')}
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* ── Auto-discover panel (embedded) ── */}
      <Collapse
        style={{ marginBottom: 16, borderRadius: 12 }}
        items={[
          {
            key: 'discover',
            label: (
              <span>
                <RadarChartOutlined
                  style={{ marginRight: 6, color: 'var(--domain-badge-bg, #6B46C1)' }}
                />
                <Text strong>{t('osRepoConfig.discover.title')}</Text>
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  {t('osRepoConfig.discover.brief')}
                </Text>
              </span>
            ),
            children: <OsDiscoverSubTab onImported={loadData} />,
          },
        ]}
      />

      <Card>
        <Spin spinning={loading}>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col flex="auto">
              <Space>
                <Select
                  mode="multiple"
                  placeholder={t('osRepoConfig.toolbar.filterTechPlaceholder')}
                  allowClear
                  style={{ minWidth: 200, maxWidth: 360 }}
                  value={filterTechElement}
                  onChange={v => {
                    setFilterTechElement(v)
                    setPage(1)
                  }}
                  options={translatedTechGroups}
                />
                <Input.Search
                  placeholder={t('osRepoConfig.toolbar.searchPlaceholder')}
                  allowClear
                  style={{ width: 240 }}
                  value={searchKeyword}
                  onChange={e => setSearchKeyword(e.target.value)}
                  onSearch={() => {
                    setPage(1)
                    loadData()
                  }}
                />
              </Space>
            </Col>
            <Col>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={loadData}>
                  {t('actions.refresh')}
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  {t('osRepoConfig.actions.addRepo')}
                </Button>
                <Button icon={<DatabaseOutlined />} onClick={() => setBatchAddModalVisible(true)}>
                  {t('osRepoConfig.actions.batchAdd')}
                </Button>
              </Space>
            </Col>
          </Row>

          {selectedRowKeys.length > 0 && (
            <div
              style={{
                background: semanticColors.bgGrayLight,
                padding: '8px 16px',
                marginBottom: 16,
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Text>
                {t('osRepoConfig.toolbar.selectedCountPrefix')}
                <strong>{selectedRowKeys.length}</strong>
                {t('osRepoConfig.toolbar.selectedCountSuffix')}
              </Text>
              <Space>
                <Button size="small" onClick={() => setSelectedRowKeys([])}>
                  {t('osRepoConfig.actions.clearSelection')}
                </Button>
                <Button size="small" icon={<DownloadOutlined />} onClick={handleExportSelected}>
                  {t('osRepoConfig.actions.exportSelected')}
                </Button>
                <Button
                  size="small"
                  icon={<TagsOutlined />}
                  onClick={() => {
                    setBatchTechValue([])
                    setBatchTechModalVisible(true)
                  }}
                >
                  {t('osRepoConfig.actions.batchSetTech')}
                </Button>
                <Button
                  type="primary"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={handleBatchCollect}
                >
                  {t('osRepoConfig.actions.batchCollect')}
                </Button>
              </Space>
            </div>
          )}
          <Table
            dataSource={data}
            columns={columns}
            rowKey="repo_config_id"
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{
              current: page,
              pageSize,
              total,
              showTotal: count => t('osRepoConfig.toolbar.total', { n: count }),
              showSizeChanger: true,
              pageSizeOptions: [10, 20, 50, 100],
              onChange: p => setPage(p),
              onShowSizeChange: (_, size) => {
                setPage(1)
                setPageSize(size)
              },
            }}
            locale={{ emptyText: <Empty description={t('osRepoConfig.toolbar.empty')} /> }}
          />
        </Spin>

        <Modal
          title={editingRecord ? t('osRepoConfig.form.editTitle') : t('osRepoConfig.form.addTitle')}
          open={modalVisible}
          onCancel={() => setModalVisible(false)}
          onOk={handleSave}
          okText={t('osRepoConfig.save')}
          width={560}
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="repo_full_name"
              label={t('osRepoConfig.form.repoFullName')}
              rules={[
                { required: true, message: t('osRepoConfig.form.repoFullNameRequired') },
                {
                  pattern: /^[\w.-]+\/[\w.-]+$/,
                  message: t('osRepoConfig.form.repoFullNamePattern'),
                },
              ]}
            >
              <Input
                disabled={!!editingRecord}
                placeholder={t('osRepoConfig.form.repoFullNamePlaceholder')}
              />
            </Form.Item>
            <Form.Item name="display_name" label={t('osRepoConfig.form.displayName')}>
              <Input placeholder={t('osRepoConfig.form.displayNamePlaceholder')} />
            </Form.Item>
            <Form.Item name="description" label={t('osRepoConfig.form.description')}>
              <Input.TextArea
                rows={2}
                placeholder={t('osRepoConfig.form.descriptionPlaceholder')}
              />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="tech_element"
                  label={t('osRepoConfig.form.techElement')}
                  rules={[{ required: true, message: t('osRepoConfig.form.techElementRequired') }]}
                >
                  <Select
                    mode="multiple"
                    placeholder={t('osRepoConfig.form.techElementPlaceholder')}
                    options={translatedTechGroups}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="language" label={t('osRepoConfig.form.language')}>
                  <Input placeholder={t('osRepoConfig.form.languagePlaceholder')} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="is_active"
                  label={t('osRepoConfig.form.isActive')}
                  valuePropName="checked"
                >
                  <Switch
                    checkedChildren={t('osRepoConfig.yes')}
                    unCheckedChildren={t('osRepoConfig.no')}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="collect_enabled"
                  label={t('osRepoConfig.form.collectEnabled')}
                  valuePropName="checked"
                >
                  <Switch
                    checkedChildren={t('osRepoConfig.yes')}
                    unCheckedChildren={t('osRepoConfig.no')}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="notes" label={t('osRepoConfig.form.notes')}>
              <Input.TextArea rows={2} placeholder={t('osRepoConfig.form.notesPlaceholder')} />
            </Form.Item>
          </Form>
        </Modal>

        {/* Collect Confirm Modal */}
        <Modal
          title={t('osRepoConfig.collectConfirm.title')}
          open={collectModalVisible}
          onCancel={() => setCollectModalVisible(false)}
          onOk={handleConfirmCollect}
          okText={t('osRepoConfig.collectConfirm.okText')}
          cancelText={t('common:actions.cancel')}
          width={420}
        >
          <p style={{ margin: 0, fontSize: 14 }}>
            {t('osRepoConfig.collectConfirm.messagePrefix')}
            <strong>{collectRecord?.repo_full_name}</strong>
            {t('osRepoConfig.collectConfirm.messageSuffix')}
          </p>
          {collectHistory && (
            <div
              style={{
                marginTop: 12,
                padding: '8px 12px',
                background: '#fffbe6',
                borderRadius: 8,
                border: '1px solid #ffe58f',
                fontSize: 13,
              }}
            >
              {t('osRepoConfig.collectConfirm.historyPrefix', {
                date: collectHistory.last_collected_at?.slice(0, 10),
                status: collectHistory.last_status_label,
              })}
              {collectHistory.last_records > 0 &&
                t('osRepoConfig.collectConfirm.historyRecords', {
                  n: collectHistory.last_records,
                })}
              {t('osRepoConfig.collectConfirm.historyRecollect')}
            </div>
          )}
        </Modal>

        {/* Batch Collect Confirm Modal */}
        <Modal
          title={t('osRepoConfig.batchCollect.title')}
          open={batchCollectModalVisible}
          onCancel={() => setBatchCollectModalVisible(false)}
          onOk={handleConfirmBatchCollect}
          okText={t('common:actions.confirm')}
          cancelText={t('common:actions.cancel')}
          width={400}
        >
          <p style={{ margin: '0 0 16px 0', fontSize: 14 }}>
            {t('osRepoConfig.batchCollect.messagePrefix')}
            <strong>{selectedRowKeys.length}</strong>
            {t('osRepoConfig.batchCollect.messageSuffix')}
          </p>
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary">{t('osRepoConfig.batchCollect.contributorsPerRepo')}</Text>
          </div>
          <InputNumber
            min={0}
            max={2000}
            value={batchContributorsPerRepo}
            onChange={v => setBatchContributorsPerRepo(v ?? 0)}
            style={{ width: '100%' }}
          />
        </Modal>

        {/* Batch Tech Element Modal */}
        <Modal
          title={t('osRepoConfig.batchTech.title')}
          open={batchTechModalVisible}
          onCancel={() => setBatchTechModalVisible(false)}
          onOk={handleBatchTechUpdate}
          okText={t('common:actions.confirm')}
          cancelText={t('common:actions.cancel')}
          confirmLoading={batchTechLoading}
          width={440}
        >
          <p style={{ margin: '0 0 12px 0', fontSize: 14 }}>
            {t('osRepoConfig.batchTech.messagePrefix')}
            <strong>{selectedRowKeys.length}</strong>
            {t('osRepoConfig.batchTech.messageSuffix')}
          </p>
          <Select
            mode="multiple"
            placeholder={t('osRepoConfig.batchTech.selectPlaceholder')}
            value={batchTechValue}
            onChange={setBatchTechValue}
            style={{ width: '100%' }}
            options={translatedTechGroups}
          />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('osRepoConfig.batchTech.hint')}
            </Text>
          </div>
        </Modal>

        {/* Batch History — 3-choice modal (some repos already collected) */}
        <Modal
          title={t('osRepoConfig.batchHistory.title')}
          open={batchHistoryModal.visible}
          onCancel={() => setBatchHistoryModal(prev => ({ ...prev, visible: false }))}
          width={480}
          footer={
            <Space>
              <Button onClick={() => setBatchHistoryModal(prev => ({ ...prev, visible: false }))}>
                {t('common:actions.cancel')}
              </Button>
              <Button
                disabled={batchHistoryModal.allIds.length === batchHistoryModal.collected.length}
                onClick={async () => {
                  const collectedIds = new Set(
                    batchHistoryModal.collected.map(c => c.repo_config_id)
                  )
                  const uncollectedIds = batchHistoryModal.allIds.filter(
                    id => !collectedIds.has(id)
                  )
                  setBatchHistoryModal(prev => ({ ...prev, visible: false }))
                  if (uncollectedIds.length > 0) {
                    setBatchCollectModalVisible(true)
                    setSelectedRowKeys(uncollectedIds as React.Key[])
                  }
                }}
              >
                {t('osRepoConfig.batchHistory.onlyNew', {
                  n: batchHistoryModal.allIds.length - batchHistoryModal.collected.length,
                })}
              </Button>
              <Button
                type="primary"
                onClick={async () => {
                  const allIds = batchHistoryModal.allIds
                  setBatchHistoryModal(prev => ({ ...prev, visible: false }))
                  await executeBatchCollect(allIds)
                }}
              >
                {t('osRepoConfig.batchHistory.collectAll', {
                  n: batchHistoryModal.allIds.length,
                })}
              </Button>
            </Space>
          }
        >
          <div
            style={{
              marginBottom: 12,
              padding: '8px 12px',
              background: '#fffbe6',
              borderRadius: 8,
              border: '1px solid #ffe58f',
              fontSize: 13,
            }}
          >
            {t('osRepoConfig.batchHistory.warning', {
              n: batchHistoryModal.collected.length,
            })}
          </div>
          <div style={{ maxHeight: 240, overflow: 'auto', fontSize: 13, marginBottom: 16 }}>
            {batchHistoryModal.collected.map(c => (
              <div key={c.repo_config_id} style={{ marginBottom: 4 }}>
                • <strong>{c.repo_full_name}</strong> — {c.last_collected_at?.slice(0, 10)}{' '}
                {c.last_status_label}
                {c.last_records > 0 &&
                  t('osRepoConfig.batchHistory.records', { n: c.last_records })}
              </div>
            ))}
          </div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            {t('osRepoConfig.batchHistory.chooseAction')}
          </Text>
        </Modal>

        {/* Batch Add Modal */}
        <Modal
          title={t('osRepoConfig.batchAdd.title')}
          open={batchAddModalVisible}
          onCancel={() => {
            setBatchAddModalVisible(false)
            setBatchAddText('')
          }}
          onOk={handleBatchAdd}
          confirmLoading={batchAddLoading}
          okText={`${t('osRepoConfig.batchAdd.okText')}${
            batchAddText.split('\n').filter(l => l.trim()).length > 0
              ? t('osRepoConfig.batchAdd.okCount', {
                  n: batchAddText.split('\n').filter(l => l.trim()).length,
                })
              : ''
          }`}
          cancelText={t('common:actions.cancel')}
          width={560}
        >
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              {t('osRepoConfig.batchAdd.techLabel')}
            </Text>
            <Select
              mode="multiple"
              style={{ width: '100%', marginTop: 4 }}
              value={batchAddTech}
              onChange={setBatchAddTech}
              options={translatedTechGroups}
              placeholder={t('osRepoConfig.batchAdd.techPlaceholder')}
            />
          </div>
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              {t('osRepoConfig.batchAdd.linksLabel')}
            </Text>
          </div>
          <Input.TextArea
            rows={8}
            placeholder={
              'https://github.com/openai/whisper\nhttps://github.com/langchain-ai/langchain\nmicrosoft/DeepSpeed'
            }
            value={batchAddText}
            onChange={e => setBatchAddText(e.target.value)}
            style={{ fontFamily: 'monospace, monospace', fontSize: 12 }}
          />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('osRepoConfig.batchAdd.autoFetchHint')}
            </Text>
          </div>
        </Modal>

        {/* Batch Tech Element Modal */}
        <Modal
          title={t('osRepoConfig.batchTech.titleCount', { n: selectedRowKeys.length })}
          open={batchTechModalVisible}
          onCancel={() => setBatchTechModalVisible(false)}
          onOk={handleBatchTechUpdate}
          confirmLoading={batchTechLoading}
          okText={t('osRepoConfig.batchTech.apply')}
          cancelText={t('common:actions.cancel')}
          width={480}
        >
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              {t('osRepoConfig.batchTech.applyMessage')}
            </Text>
          </div>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            value={batchTechValue}
            onChange={setBatchTechValue}
            options={translatedTechGroups}
            placeholder={t('osRepoConfig.batchTech.selectPlaceholderMulti')}
          />
          <div
            style={{
              marginTop: 12,
              padding: '8px 12px',
              background: '#f6f8fa',
              borderRadius: 8,
              fontSize: 12,
            }}
          >
            {t('osRepoConfig.batchTech.hintPrefix')}
            <Text code>{t('osRepoConfig.batchTech.hintUnion')}</Text>
            {t('osRepoConfig.batchTech.hintSuffix')}
          </div>
        </Modal>

        {/* Purge Confirm Modal */}
        <Modal
          title={t('osRepoConfig.purge.title', {
            repo: purgeRecord?.repo_full_name ?? '',
          })}
          open={purgeModalVisible}
          onCancel={() => setPurgeModalVisible(false)}
          onOk={handleConfirmPurge}
          okText={t('osRepoConfig.purge.okText')}
          cancelText={t('common:actions.cancel')}
          okButtonProps={{
            danger: true,
            disabled: purgeConfirmText !== purgeRecord?.repo_full_name,
            loading: purgeExecuting,
          }}
          width={520}
        >
          <Spin spinning={purgeLoading}>
            {purgePreview && !purgePreview.repo_found && (
              <p style={{ fontSize: 14 }}>{t('osRepoConfig.purge.nothing')}</p>
            )}
            {purgePreview && purgePreview.repo_found && (
              <div style={{ fontSize: 14 }}>
                <p>
                  {t('osRepoConfig.purge.warningPrefix')}
                  <strong>{purgePreview.contributions}</strong>
                  {t('osRepoConfig.purge.warningMiddle')}
                  <strong style={{ color: '#cf1322' }}>
                    {' '}
                    {purgePreview.developers_exclusive}{' '}
                  </strong>
                  {t('osRepoConfig.purge.warningSkills', {
                    skills: purgePreview.skills,
                    embeddings: purgePreview.embeddings,
                    raw: purgePreview.raw,
                  })}
                </p>
                <p>
                  <strong>{purgePreview.developers_shared}</strong>
                  {t('osRepoConfig.purge.retainedShared')}
                  <strong> {purgePreview.developers_protected} </strong>
                  {t('osRepoConfig.purge.retainedProtected')}
                </p>
                <p style={{ color: '#cf1322' }}>{t('osRepoConfig.purge.irreversible')}</p>
              </div>
            )}
            {!purgeLoading && (
              <>
                <div style={{ margin: '12px 0 8px' }}>
                  <Text type="secondary">
                    {t('osRepoConfig.purge.promptPrefix')}{' '}
                    <Text code>{purgeRecord?.repo_full_name}</Text>{' '}
                    {t('osRepoConfig.purge.promptSuffix')}
                  </Text>
                </div>
                <Input
                  value={purgeConfirmText}
                  onChange={e => setPurgeConfirmText(e.target.value)}
                  placeholder={purgeRecord?.repo_full_name}
                />
                <div style={{ marginTop: 12 }}>
                  <Switch
                    checked={purgeDeleteConfig}
                    onChange={setPurgeDeleteConfig}
                    size="small"
                    style={{ marginRight: 8 }}
                  />
                  <Text type="secondary">{t('osRepoConfig.purge.deleteConfig')}</Text>
                </div>
              </>
            )}
          </Spin>
        </Modal>
      </Card>
    </div>
  )
}

export default OSRepoConfigSubTab

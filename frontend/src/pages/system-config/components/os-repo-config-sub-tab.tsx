import { useState, useEffect, useCallback } from 'react'
import { semanticColors } from '../../../theme'
import {
  Card,
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
} from '@ant-design/icons'
import { api } from '../../../services/api'
import type { OSPurgePreview, OSRepoConfig } from '../../../types'
import { getErrorMessage } from './utils'

const { Text } = Typography

const TECH_ELEMENTS = [
  { value: 'ai', label: '人工智能', color: semanticColors.osPurple },
  { value: 'robotics', label: '机器人', color: semanticColors.osGreen },
  { value: 'data_science', label: '数据科学', color: semanticColors.osBlue },
  { value: 'networks', label: '网络与通信', color: semanticColors.osOrangeDark },
  { value: 'systems', label: '系统与软件', color: semanticColors.osPurple },
  { value: 'security', label: '信息安全', color: semanticColors.osRed },
]

const getTechElementLabel = (code: string) => {
  const item = TECH_ELEMENTS.find((t) => t.value === code)
  return item?.label || code
}

const getTechElementColor = (code: string) => {
  const item = TECH_ELEMENTS.find((t) => t.value === code)
  return item?.color || '#999'
}

const OSRepoConfigSubTab: React.FC = () => {
  const [data, setData] = useState<OSRepoConfig[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState<OSRepoConfig | null>(null)
  const [form] = Form.useForm()
  const [filterTechElement, setFilterTechElement] = useState<string | undefined>(undefined)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [collectingIds, setCollectingIds] = useState<Set<number>>(new Set())
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [collectRecord, setCollectRecord] = useState<OSRepoConfig | null>(null)
  const [collectHistory, setCollectHistory] = useState<{ last_status_label: string; last_collected_at: string; last_records: number } | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [batchCollectModalVisible, setBatchCollectModalVisible] = useState(false)
  const [batchContributorsPerRepo, setBatchContributorsPerRepo] = useState<number>(0)
  const [batchHistoryModal, setBatchHistoryModal] = useState<{
    visible: boolean
    collected: { repo_config_id: number; repo_full_name: string; last_status_label: string; last_collected_at: string; last_records: number }[]
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
  const [batchAddTech, setBatchAddTech] = useState('ai')
  const [batchAddLoading, setBatchAddLoading] = useState(false)
  const [purgeDeleteConfig, setPurgeDeleteConfig] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page, page_size: 10 }
      if (filterTechElement) params.tech_element = filterTechElement
      if (searchKeyword) params.q = searchKeyword
      const response = await api.openSource.listRepoConfigs(params)
      setData(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch {
      message.error('加载仓库配置失败')
    } finally {
      setLoading(false)
    }
  }, [page, filterTechElement, searchKeyword])

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
        message.success('仓库配置已更新')
      } else {
        await api.openSource.createRepoConfig(values)
        message.success('仓库配置已创建')
      }
      setModalVisible(false)
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, '保存失败'))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.openSource.deleteRepoConfig(id)
      message.success('仓库配置已删除')
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, '删除失败'))
    }
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
      message.error(getErrorMessage(error, '获取清理预览失败'))
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
        `已清理 ${result.repo_full_name} 的采集数据：删除贡献 ${result.contributions} 条、` +
          `独占人才 ${result.developers_exclusive} 名` +
          (result.config_deleted ? '，仓库配置已一并删除' : '')
      )
      setPurgeModalVisible(false)
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, '清理失败'))
    } finally {
      setPurgeExecuting(false)
    }
  }

  const handleBatchAdd = async () => {
    const lines = batchAddText.split('\n').map(l => l.trim()).filter(Boolean)
    if (lines.length === 0) {
      message.warning('请输入至少一个仓库链接')
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
            <Text strong style={{ color: '#52c41a' }}>✅ 创建成功 {created.length} 个</Text>
            {created.map((c: { repo_full_name: string; language?: string; stars_count?: number }) => (
              <div key={c.repo_full_name} style={{ fontSize: 12, marginLeft: 16, marginTop: 2 }}>
                • {c.repo_full_name}
                {c.language && ` (${c.language}`}
                {c.stars_count != null && c.stars_count > 0 && `, ${c.stars_count >= 1000 ? `${(c.stars_count / 1000).toFixed(1)}k` : c.stars_count} stars`}
                {c.language && ')'}
              </div>
            ))}
          </div>
        )
      }
      if (skipped.length > 0) {
        parts.push(
          <div key="skipped" style={{ marginBottom: 12 }}>
            <Text strong style={{ color: '#faad14' }}>⚠️ 已存在/跳过 {skipped.length} 个</Text>
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
            <Text strong style={{ color: '#ff4d4f' }}>❌ 获取失败 {failed.length} 个</Text>
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
          title: '批量添加结果',
          width: 520,
          content: <div style={{ maxHeight: 400, overflow: 'auto' }}>{parts}</div>,
        })
      }
      loadData()
    } catch (error) {
      message.error(getErrorMessage(error, '批量添加失败'))
    } finally {
      setBatchAddLoading(false)
    }
  }

  const handleConfirmCollect = async () => {
    if (!collectRecord) return
    try {
      setCollectModalVisible(false)
      setCollectingIds((prev) => new Set(prev).add(collectRecord.repo_config_id))
      await api.openSource.collectRepo(collectRecord.repo_config_id)
      message.success(`已启动 ${collectRecord.repo_full_name} 的采集任务`)
    } catch (error) {
      message.error(getErrorMessage(error, '启动采集失败'))
    } finally {
      setCollectingIds((prev) => {
        const next = new Set(prev)
        next.delete(collectRecord.repo_config_id)
        return next
      })
    }
  }

  const handleBatchCollect = async () => {
    if (selectedRowKeys.length === 0) return
    const ids = selectedRowKeys.map((k) => Number(k))
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
      ids.forEach((id) => {
        setCollectingIds((prev) => new Set(prev).add(id))
      })
      const response = await api.openSource.collectBatchRepos(ids, batchContributorsPerRepo)
      const { created, skipped } = response.data
      if (created.length > 0) {
        message.success(`已成功启动 ${created.length} 个仓库的采集任务`)
      }
      if (skipped.length > 0) {
        const reasons = skipped.map((s: { repo_full_name?: string; reason: string }) =>
          `${s.repo_full_name || '未知仓库'}: ${s.reason}`
        )
        Modal.warning({
          title: `${skipped.length} 个仓库被跳过`,
          content: (
            <div style={{ maxHeight: 240, overflow: 'auto' }}>
              {reasons.map((r: string, i: number) => (
                <div key={i} style={{ marginBottom: 4 }}>{r}</div>
              ))}
            </div>
          ),
        })
      }
      if (created.length === 0 && skipped.length === 0) {
        message.info('未启动任何采集任务')
      }
      setSelectedRowKeys([])
    } catch (error) {
      message.error(getErrorMessage(error, '批量启动采集失败'))
    } finally {
      ids.forEach((id) => {
        setCollectingIds((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
      })
    }
  }

  const handleConfirmBatchCollect = async () => {
    setBatchCollectModalVisible(false)
    const ids = selectedRowKeys.map((k) => Number(k))
    await executeBatchCollect(ids)
  }

  const columns = [
    {
      title: '显示名称',
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
      title: '仓库全名',
      dataIndex: 'repo_full_name',
      key: 'repo_full_name',
      render: (name: string) => (
        <a href={`https://github.com/${name}`} target="_blank" rel="noopener noreferrer">
          {name}
        </a>
      ),
    },
    {
      title: '技术领域',
      dataIndex: 'tech_element',
      key: 'tech_element',
      width: 140,
      render: (codes: string[] | string) => {
        const list = Array.isArray(codes) ? codes : [codes]
        return (
          <Space size={2} wrap>
            {list.map((code) => (
              <Tag key={code} color={getTechElementColor(code)} style={{ margin: 0 }}>
                {getTechElementLabel(code)}
              </Tag>
            ))}
          </Space>
        )
      },
    },

    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: OSRepoConfig) => (
        <Space>
          <Tooltip title="开始采集">
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleCollect(record)}
              loading={collectingIds.has(record.repo_config_id)}
              disabled={!record.collect_enabled || collectingIds.has(record.repo_config_id)}
            >
              采集
            </Button>
          </Tooltip>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此仓库配置？"
            onConfirm={() => handleDelete(record.repo_config_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
          <Tooltip title="清理该仓库的采集数据（贡献/独占人才等）">
            <Button
              type="link"
              size="small"
              danger
              icon={<ClearOutlined />}
              onClick={() => handlePurge(record)}
            >
              清理数据
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <Spin spinning={loading}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Space>
              <Select
                placeholder="筛选技术领域"
                allowClear
                style={{ width: 160 }}
                value={filterTechElement}
                onChange={(v) => { setFilterTechElement(v); setPage(1) }}
                options={TECH_ELEMENTS}
              />
              <Input.Search
                placeholder="搜索仓库名称..."
                allowClear
                style={{ width: 240 }}
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onSearch={() => { setPage(1); loadData() }}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                新增仓库
              </Button>
              <Button icon={<DatabaseOutlined />} onClick={() => setBatchAddModalVisible(true)}>
                批量添加
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
              已选择 <strong>{selectedRowKeys.length}</strong> 个仓库
            </Text>
            <Space>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>
                取消选择
              </Button>
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={handleBatchCollect}
              >
                批量采集
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
            pageSize: 10,
            total,
            showTotal: (t) => `共 ${t} 个仓库`,
            onChange: (p) => setPage(p),
          }}
          locale={{ emptyText: <Empty description="暂无仓库配置" /> }}
        />
      </Spin>

      <Modal
        title={editingRecord ? '编辑仓库配置' : '新增仓库配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        okText="保存"
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="repo_full_name"
            label="GitHub 仓库全名"
            rules={[
              { required: true, message: '请输入仓库全名' },
              { pattern: /^[\w.-]+\/[\w.-]+$/, message: '格式应为 owner/repo' },
            ]}
          >
            <Input disabled={!!editingRecord} placeholder="如 pytorch/pytorch" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称">
            <Input placeholder="如 PyTorch" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="仓库描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="tech_element"
                label="技术领域（可多选）"
                rules={[{ required: true, message: '请选择技术领域' }]}
              >
                <Select mode="multiple" placeholder="选择技术领域" options={TECH_ELEMENTS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="language" label="主要语言">
                <Input placeholder="如 Python" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_active" label="启用展示" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="collect_enabled" label="参与采集" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="管理员备注" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Collect Confirm Modal */}
      <Modal
        title="确认采集"
        open={collectModalVisible}
        onCancel={() => setCollectModalVisible(false)}
        onOk={handleConfirmCollect}
        okText="确认采集"
        cancelText="取消"
        width={420}
      >
        <p style={{ margin: 0, fontSize: 14 }}>
          确认要采集 <strong>{collectRecord?.repo_full_name}</strong> 的贡献者数据吗？
        </p>
        {collectHistory && (
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#fffbe6', borderRadius: 8, border: '1px solid #ffe58f', fontSize: 13 }}>
            ⚠️ 该仓库已于 {collectHistory.last_collected_at?.slice(0, 10)} {collectHistory.last_status_label}
            {collectHistory.last_records > 0 && `（${collectHistory.last_records} 条记录）`}，确认要重新采集吗？
          </div>
        )}
      </Modal>

      {/* Batch Collect Confirm Modal */}
      <Modal
        title="确认批量采集"
        open={batchCollectModalVisible}
        onCancel={() => setBatchCollectModalVisible(false)}
        onOk={handleConfirmBatchCollect}
        okText="确认"
        cancelText="取消"
        width={400}
      >
        <p style={{ margin: '0 0 16px 0', fontSize: 14 }}>
          确认要批量采集 <strong>{selectedRowKeys.length}</strong> 个仓库的贡献者数据吗？
        </p>
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary">每个仓库采集贡献者数量（0=全部）</Text>
        </div>
        <InputNumber
          min={0}
          max={2000}
          value={batchContributorsPerRepo}
          onChange={(v) => setBatchContributorsPerRepo(v ?? 0)}
          style={{ width: '100%' }}
        />
      </Modal>

      {/* Batch History — 3-choice modal (some repos already collected) */}
      <Modal
        title="部分仓库已采集过"
        open={batchHistoryModal.visible}
        onCancel={() => setBatchHistoryModal((prev) => ({ ...prev, visible: false }))}
        width={480}
        footer={
          <Space>
            <Button onClick={() => setBatchHistoryModal((prev) => ({ ...prev, visible: false }))}>
              取消
            </Button>
            <Button
              disabled={batchHistoryModal.allIds.length === batchHistoryModal.collected.length}
              onClick={async () => {
                const collectedIds = new Set(batchHistoryModal.collected.map((c) => c.repo_config_id))
                const uncollectedIds = batchHistoryModal.allIds.filter((id) => !collectedIds.has(id))
                setBatchHistoryModal((prev) => ({ ...prev, visible: false }))
                if (uncollectedIds.length > 0) {
                  setBatchCollectModalVisible(true)
                  setSelectedRowKeys(uncollectedIds as React.Key[])
                }
              }}
            >
              只采集未采集的（{batchHistoryModal.allIds.length - batchHistoryModal.collected.length} 个）
            </Button>
            <Button
              type="primary"
              onClick={async () => {
                const allIds = batchHistoryModal.allIds
                setBatchHistoryModal((prev) => ({ ...prev, visible: false }))
                await executeBatchCollect(allIds)
              }}
            >
              继续全部采集（{batchHistoryModal.allIds.length} 个）
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 12, padding: '8px 12px', background: '#fffbe6', borderRadius: 8, border: '1px solid #ffe58f', fontSize: 13 }}>
          ⚠️ 以下 {batchHistoryModal.collected.length} 个仓库之前已采集过：
        </div>
        <div style={{ maxHeight: 240, overflow: 'auto', fontSize: 13, marginBottom: 16 }}>
          {batchHistoryModal.collected.map((c) => (
            <div key={c.repo_config_id} style={{ marginBottom: 4 }}>
              • <strong>{c.repo_full_name}</strong> — {c.last_collected_at?.slice(0, 10)} {c.last_status_label}
              {c.last_records > 0 && `（${c.last_records} 条）`}
            </div>
          ))}
        </div>
        <Text type="secondary" style={{ fontSize: 13 }}>
          请选择操作方式：
        </Text>
      </Modal>

      {/* Batch Add Modal */}
      <Modal
        title="批量添加仓库"
        open={batchAddModalVisible}
        onCancel={() => { setBatchAddModalVisible(false); setBatchAddText('') }}
        onOk={handleBatchAdd}
        confirmLoading={batchAddLoading}
        okText={`添加并自动获取信息${batchAddText.split('\n').filter(l => l.trim()).length > 0 ? ` (${batchAddText.split('\n').filter(l => l.trim()).length} 个)` : ''}`}
        cancelText="取消"
        width={560}
      >
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>技术方向（统一应用到整批）</Text>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={batchAddTech}
            onChange={setBatchAddTech}
            options={TECH_ELEMENTS}
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            仓库链接（每行一个，支持 GitHub URL 或 owner/repo 格式）
          </Text>
        </div>
        <Input.TextArea
          rows={8}
          placeholder={'https://github.com/openai/whisper\nhttps://github.com/langchain-ai/langchain\nmicrosoft/DeepSpeed'}
          value={batchAddText}
          onChange={e => setBatchAddText(e.target.value)}
          style={{ fontFamily: 'monospace, monospace', fontSize: 12 }}
        />
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            系统将自动通过 GitHub API 获取仓库名称、描述、主要语言和 Star 数
          </Text>
        </div>
      </Modal>

      {/* Purge Confirm Modal */}
      <Modal
        title={`清理采集数据 - ${purgeRecord?.repo_full_name ?? ''}`}
        open={purgeModalVisible}
        onCancel={() => setPurgeModalVisible(false)}
        onOk={handleConfirmPurge}
        okText="确认清理"
        cancelText="取消"
        okButtonProps={{
          danger: true,
          disabled: purgeConfirmText !== purgeRecord?.repo_full_name,
          loading: purgeExecuting,
        }}
        width={520}
      >
        <Spin spinning={purgeLoading}>
          {purgePreview && !purgePreview.repo_found && (
            <p style={{ fontSize: 14 }}>
              该仓库尚未采集过数据（无仓库与贡献记录），清理不会产生任何删除。
            </p>
          )}
          {purgePreview && purgePreview.repo_found && (
            <div style={{ fontSize: 14 }}>
              <p>
                将删除 <strong>{purgePreview.contributions}</strong> 条贡献记录、
                <strong style={{ color: '#cf1322' }}> {purgePreview.developers_exclusive} </strong>
                名独占人才（连带语言技能 {purgePreview.skills} 条、向量 {purgePreview.embeddings}{' '}
                条、原始数据 {purgePreview.raw} 条），以及该仓库本身。
              </p>
              <p>
                <strong>{purgePreview.developers_shared}</strong> 名人才因被其他已配置仓库引用而保留，
                <strong> {purgePreview.developers_protected} </strong>
                名人才因被收藏或加入人才池而保留。
              </p>
              <p style={{ color: '#cf1322' }}>此操作不可恢复，采集任务历史记录会保留。</p>
            </div>
          )}
          {!purgeLoading && (
            <>
              <div style={{ margin: '12px 0 8px' }}>
                <Text type="secondary">
                  请输入仓库全名 <Text code>{purgeRecord?.repo_full_name}</Text> 以确认清理
                </Text>
              </div>
              <Input
                value={purgeConfirmText}
                onChange={(e) => setPurgeConfirmText(e.target.value)}
                placeholder={purgeRecord?.repo_full_name}
              />
              <div style={{ marginTop: 12 }}>
                <Switch
                  checked={purgeDeleteConfig}
                  onChange={setPurgeDeleteConfig}
                  size="small"
                  style={{ marginRight: 8 }}
                />
                <Text type="secondary">同时删除该仓库的配置行</Text>
              </div>
            </>
          )}
        </Spin>
      </Modal>
    </Card>
  )
}

export default OSRepoConfigSubTab

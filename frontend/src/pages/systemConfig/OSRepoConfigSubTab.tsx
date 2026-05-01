import { useState, useEffect, useCallback } from 'react'
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
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  GithubOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { OSRepoConfig } from '../../types'
import { getErrorMessage } from './utils'

const { Text } = Typography

const TECH_ELEMENTS = [
  { value: 'ai', label: '人工智能', color: '#2D3748' },
  { value: 'robotics', label: '机器人', color: '#38A169' },
  { value: 'data_science', label: '数据科学', color: '#3182CE' },
  { value: 'networks', label: '网络与通信', color: '#DD6B20' },
  { value: 'systems', label: '系统与软件', color: '#805AD5' },
  { value: 'security', label: '信息安全', color: '#E53E3E' },
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

  const handleCollect = (record: OSRepoConfig) => {
    setCollectRecord(record)
    setCollectModalVisible(true)
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
      width: 120,
      render: (code: string) => (
        <Tag color={getTechElementColor(code)}>{getTechElementLabel(code)}</Tag>
      ),
    },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      width: 100,
      render: (lang: string) => lang || '-',
    },
    {
      title: 'Stars',
      dataIndex: 'stars_count',
      key: 'stars_count',
      width: 100,
      render: (count: number) => count?.toLocaleString() || 0,
    },
    {
      title: '展示',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>{active ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '采集',
      dataIndex: 'collect_enabled',
      key: 'collect_enabled',
      width: 80,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'processing' : 'default'}>{enabled ? '参与' : '跳过'}</Tag>
      ),
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
            </Space>
          </Col>
        </Row>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="repo_config_id"
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
                label="技术领域"
                rules={[{ required: true, message: '请选择技术领域' }]}
              >
                <Select placeholder="选择技术领域" options={TECH_ELEMENTS} />
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
        okText="确认"
        cancelText="取消"
        width={360}
      >
        <p style={{ margin: 0, fontSize: 14 }}>
          确认要采集 <strong>{collectRecord?.repo_full_name}</strong> 的贡献者数据吗？
        </p>
      </Modal>
    </Card>
  )
}

export default OSRepoConfigSubTab

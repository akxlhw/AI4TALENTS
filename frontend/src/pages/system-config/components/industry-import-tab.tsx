import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { UploadProps } from 'antd'
import {
  ApiOutlined,
  BuildOutlined,
  DeleteOutlined,
  DownloadOutlined,
  InboxOutlined,
  KeyOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../services/api'
import type { IndustryImportReport } from '../../../services/api/industry'
import { useIndustryPositions } from '../../../hooks/useIndustryQueries'
import { queryKeys } from '../../../hooks/queryClient'
import { getErrorMessage } from '../../../utils'

const { Dragger } = Upload
const { Text, Title } = Typography

const MAX_SIZE_BYTES = 20 * 1024 * 1024

/**
 * Industry talent JSONL import tab (super_admin, system-config).
 * Requires a target position; backend performs incremental upsert
 * (empty fields never overwrite, absent rows untouched, recruiting
 * state preserved).
 */
const IndustryImportTab: React.FC = () => {
  const queryClient = useQueryClient()
  const { data: positions, isLoading: positionsLoading } = useIndustryPositions('open')
  const [positionId, setPositionId] = useState<number | null>(null)
  const [batch, setBatch] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<IndustryImportReport | null>(null)

  const beforeUpload: UploadProps['beforeUpload'] = file => {
    if (!file.name.endsWith('.jsonl')) {
      message.error('请上传 .jsonl 文件')
      return Upload.LIST_IGNORE
    }
    if (file.size > MAX_SIZE_BYTES) {
      message.error('文件超过 20MB 上限')
      return Upload.LIST_IGNORE
    }
    setSelectedFile(file)
    return false
  }

  const onRemove = () => {
    setSelectedFile(null)
    setReport(null)
  }

  const handleImport = async () => {
    if (!positionId) {
      message.warning('请先选择目标岗位')
      return
    }
    if (!selectedFile) {
      message.warning('请先选择 JSONL 文件')
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.industry.importUpload(selectedFile, positionId, batch || undefined)
      setReport(res.data)
      setSelectedFile(null)
      message.success(
        `导入完成：人才新增 ${res.data.talents_inserted} / 更新 ${res.data.talents_updated}，` +
          `关联新增 ${res.data.links_inserted} / 更新 ${res.data.links_updated}，` +
          `${res.data.skipped} 行跳过`
      )
      // Fresh candidates may now appear in the talent pool / position aggregates
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
    } catch (e) {
      message.error(getErrorMessage(e, '导入失败'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title={<><ApiOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />Agent 自动导入通道</>}>
        <AgentChannelGuide />
      </Card>
      <Card>
        <Title level={5}>
          <BuildOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
          行业人才导入
        </Title>
        <Text type="secondary">
          上传 smart-talent-sourcing skill 产出的候选人 JSONL（schema
          v1.0）。导入为增量更新：空字段不覆盖已有数据，已有招聘状态（触达/状态/备注）会被保留。
        </Text>

        <div style={{ marginTop: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Select
            placeholder="选择目标岗位（必选）"
            style={{ minWidth: 280, flex: 1 }}
            loading={positionsLoading}
            value={positionId ?? undefined}
            onChange={v => setPositionId(v)}
            options={(positions || []).map(p => ({
              value: p.position_id,
              label: `${p.title}${p.department ? `（${p.department}）` : ''}`,
            }))}
            showSearch
            optionFilterProp="label"
          />
          <Input
            placeholder="导入批次标识（可选，如 2026-08-llm）"
            style={{ minWidth: 240, flex: 1 }}
            value={batch}
            onChange={e => setBatch(e.target.value)}
            maxLength={50}
            allowClear
          />
        </div>

        <div style={{ marginTop: 16 }}>
          <Dragger
            accept=".jsonl"
            maxCount={1}
            beforeUpload={beforeUpload}
            onRemove={onRemove}
            fileList={selectedFile ? [{ uid: '-1', name: selectedFile.name, status: 'done' }] : []}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 JSONL 文件到此区域上传</p>
            <p className="ant-upload-hint">仅支持单个 .jsonl 文件（skill 输出格式，≤ 20MB）</p>
          </Dragger>
        </div>

        <div style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            loading={uploading}
            onClick={handleImport}
            disabled={!selectedFile || !positionId}
          >
            开始导入
          </Button>
        </div>
      </Card>

      {report && (
        <Card title="导入报告">
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="总行数">{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label="解析成功">{report.total_parsed}</Descriptions.Item>
            <Descriptions.Item label="人才新增">
              <Tag color="green">{report.talents_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="人才更新">
              <Tag color="blue">{report.talents_updated}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="关联新增">
              <Tag color="green">{report.links_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="关联更新">
              <Tag color="blue">{report.links_updated}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="跳过">
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="警告（缺公司）">
              <Tag color={report.warnings > 0 ? 'warning' : 'default'}>{report.warnings}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {report.warnings > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message={`${report.warnings} 行缺少 current_org`}
              description="缺少现任公司时去重区分度较弱（dedup_hash 退化），建议人工关注这些记录。"
            />
          )}

          {report.aborted && (
            <Alert
              style={{ marginTop: 16 }}
              type="error"
              showIcon
              message="导入已中止：未写入任何数据"
              description="文件中没有可导入的有效记录（空文件或全部行无效），请检查文件内容后重新上传。"
            />
          )}

          {report.skip_reasons.length > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={`${report.skip_reasons.length} 行被跳过（前 50 条）`}
              description={
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  {report.skip_reasons.slice(0, 50).map((r, i) => (
                    <div key={i} style={{ fontSize: 12 }}>
                      <Text type="secondary">行 {r.line}：</Text>
                      <Text>{r.reason}</Text>
                    </div>
                  ))}
                </div>
              }
            />
          )}
        </Card>
      )}

      {/* Batch management — delete bad imports */}
      <Card title="导入批次管理">
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          选择岗位查看已导入的批次。如果某次导入的数据质量不满意，可以删除该批次（候选人关联和打分会一并删除；不再被任何岗位关联的人才也会被清理）。
        </Text>
        <BatchManager />
      </Card>
    </Space>
  )
}

export default IndustryImportTab

// --- Batch Manager sub-component ---

const BatchManager: React.FC = () => {
  const queryClient = useQueryClient()
  const { data: positions } = useIndustryPositions()
  const [selectedPosition, setSelectedPosition] = useState<number | null>(null)
  const [batches, setBatches] = useState<
    { batch: string | null; count: number; latest: string | null }[]
  >([])
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [exporting, setExporting] = useState<string | null>(null)

  const loadBatches = async (positionId: number) => {
    setLoading(true)
    try {
      const res = await api.industry.listBatches(positionId)
      setBatches(res.data)
    } catch (e) {
      message.error(getErrorMessage(e, '加载批次失败'))
      setBatches([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (batchName: string | null) => {
    if (!selectedPosition) return
    setDeleting(batchName ?? '__none__')
    try {
      const res = await api.industry.deleteBatch(selectedPosition, batchName)
      message.success(
        `已删除 ${res.data.links_deleted} 条关联，清理 ${res.data.talents_deleted} 个孤立人才`
      )
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
      await loadBatches(selectedPosition)
    } catch (e) {
      message.error(getErrorMessage(e, '删除失败'))
    } finally {
      setDeleting(null)
    }
  }

  const handleExport = async (batchName?: string | null) => {
    if (!selectedPosition) return
    const key = batchName === null ? '__none__' : (batchName ?? '__all__')
    setExporting(key)
    try {
      const res = await api.industry.exportPosition(selectedPosition, batchName)
      // Trigger browser download from the blob
      const disposition = res.headers['content-disposition'] || ''
      const match = disposition.match(/filename="?([^"]+)"?/)
      const filename =
        match?.[1] ||
        `industry_position_${selectedPosition}${batchName ? `_${batchName}` : '_all'}.jsonl`
      const url = window.URL.createObjectURL(
        new Blob([res.data], { type: 'application/x-jsonlines' })
      )
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      message.success(`已导出 ${filename}`)
    } catch (e) {
      message.error(getErrorMessage(e, '导出失败'))
    } finally {
      setExporting(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="选择岗位查看批次"
          style={{ width: 360 }}
          value={selectedPosition ?? undefined}
          onChange={v => {
            setSelectedPosition(v)
            if (v) loadBatches(v)
            else setBatches([])
          }}
          options={(positions || []).map(p => ({
            value: p.position_id,
            label: p.title,
          }))}
          allowClear
          showSearch
          optionFilterProp="label"
        />
        {selectedPosition && (
          <Button
            icon={<DownloadOutlined />}
            loading={exporting === '__all__'}
            onClick={() => handleExport(undefined)}
          >
            导出全部
          </Button>
        )}
      </Space>

      {selectedPosition && (
        <Table
          size="small"
          loading={loading}
          dataSource={batches}
          rowKey={(r: { batch: string | null }) => r.batch ?? '__none__'}
          pagination={false}
          locale={{ emptyText: '暂无导入批次' }}
          columns={[
            {
              title: '批次',
              dataIndex: 'batch',
              key: 'batch',
              render: (v: string | null) => v ?? '（无批次）',
            },
            { title: '候选人数', dataIndex: 'count', key: 'count', width: 100 },
            {
              title: '导入时间',
              dataIndex: 'latest',
              key: 'latest',
              width: 180,
              render: (v: string | null) => (v ? v.slice(0, 19).replace('T', ' ') : '—'),
            },
            {
              title: '操作',
              key: 'action',
              width: 180,
              render: (_: unknown, record: { batch: string | null }) => (
                <Space size={4}>
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    loading={exporting === (record.batch ?? '__none__')}
                    onClick={() => handleExport(record.batch)}
                  >
                    导出
                  </Button>
                  <Popconfirm
                    title="确认删除该批次？"
                    description="该批次的全部候选人关联和打分将被删除。"
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => handleDelete(record.batch)}
                  >
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleting === (record.batch ?? '__none__')}
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      )}
    </>
  )
}

// --- Agent import channel guide (API keys now live in the shared API Key tab) ---

const AgentChannelGuide: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="API Key 已统一迁移至「API Key 管理」"
        description={
          <>
            导入通道鉴权已并入开放 API Key 体系（scope：
            <Text code>industry:write</Text>）。创建、吊销、限流均在「API Key
            管理」页完成；此处仅保留调用方式说明。
          </>
        }
      />
      <Button
        type="primary"
        icon={<KeyOutlined />}
        onClick={() => navigate('/system-config?tab=api-keys')}
      >
        前往 API Key 管理
      </Button>

      <Alert
        type="info"
        style={{ marginTop: 16 }}
        message="调用示例"
        description={
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              第一步：查询岗位 ID
            </Text>
            <pre style={{ margin: 0, fontSize: 12, overflow: 'auto' }}>{`curl "${window.location.origin}/api/v1/industry/positions?status=open"   -H "X-API-Key: <你的Key>"`}</pre>
            <Text type="secondary" style={{ display: 'block', margin: '12px 0 8px' }}>
              第二步：导入候选人 JSONL
            </Text>
            <pre style={{ margin: 0, fontSize: 12, overflow: 'auto' }}>{`curl -X POST "${window.location.origin}/api/v1/industry/import?position_id=<岗位ID>&batch=<批次>"   -H "X-API-Key: <你的Key>"   -H "Content-Type: application/x-jsonlines"   --data-binary @scored.jsonl`}</pre>
          </>
        }
      />
    </div>
  )
}

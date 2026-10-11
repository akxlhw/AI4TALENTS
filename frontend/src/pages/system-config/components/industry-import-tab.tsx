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
import { useTranslation } from 'react-i18next'
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
import '../../../i18n/namespaces/system-config'

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
  const { t } = useTranslation(['systemConfig', 'common'])
  const queryClient = useQueryClient()
  const { data: positions, isLoading: positionsLoading } = useIndustryPositions('open')
  const [positionId, setPositionId] = useState<number | null>(null)
  const [batch, setBatch] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<IndustryImportReport | null>(null)

  const beforeUpload: UploadProps['beforeUpload'] = file => {
    if (!file.name.endsWith('.jsonl')) {
      message.error(t('common.invalidJsonl'))
      return Upload.LIST_IGNORE
    }
    if (file.size > MAX_SIZE_BYTES) {
      message.error(t('industryImport.tooLarge'))
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
      message.warning(t('industryImport.noPositionSelected'))
      return
    }
    if (!selectedFile) {
      message.warning(t('common.noFileSelected'))
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.industry.importUpload(selectedFile, positionId, batch || undefined)
      setReport(res.data)
      setSelectedFile(null)
      message.success(
        t('industryImport.importDone', {
          inserted: res.data.talents_inserted,
          updated: res.data.talents_updated,
          linksInserted: res.data.links_inserted,
          linksUpdated: res.data.links_updated,
          skipped: res.data.skipped,
        })
      )
      // Fresh candidates may now appear in the talent pool / position aggregates
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
    } catch (e) {
      message.error(getErrorMessage(e, t('common.importFailed')))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title={<><ApiOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />{t('industryImport.agentChannel.cardTitle')}</>}>
        <AgentChannelGuide />
      </Card>
      <Card>
        <Title level={5}>
          <BuildOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
          {t('industryImport.heading')}
        </Title>
        <Text type="secondary">
          {t('industryImport.description')}
        </Text>

        <div style={{ marginTop: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Select
            placeholder={t('industryImport.selectPositionPlaceholder')}
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
            placeholder={t('industryImport.batchPlaceholder')}
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
            <p className="ant-upload-text">{t('common.uploadDragText')}</p>
            <p className="ant-upload-hint">{t('industryImport.uploadHint')}</p>
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
            {t('common.startImport')}
          </Button>
        </div>
      </Card>

      {report && (
        <Card title={t('industryImport.report.title')}>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label={t('industryImport.report.totalLines')}>{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.parsed')}>{report.total_parsed}</Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.talentsInserted')}>
              <Tag color="green">{report.talents_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.talentsUpdated')}>
              <Tag color="blue">{report.talents_updated}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.linksInserted')}>
              <Tag color="green">{report.links_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.linksUpdated')}>
              <Tag color="blue">{report.links_updated}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.skipped')}>
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('industryImport.report.warnings')}>
              <Tag color={report.warnings > 0 ? 'warning' : 'default'}>{report.warnings}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {report.warnings > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message={t('industryImport.report.missingOrgTitle', { count: report.warnings })}
              description={t('industryImport.report.missingOrgDescription')}
            />
          )}

          {report.aborted && (
            <Alert
              style={{ marginTop: 16 }}
              type="error"
              showIcon
              message={t('industryImport.report.abortedTitle')}
              description={t('industryImport.report.abortedDescription')}
            />
          )}

          {report.skip_reasons.length > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={t('common.skipSummary', { count: report.skip_reasons.length })}
              description={
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  {report.skip_reasons.slice(0, 50).map((r, i) => (
                    <div key={i} style={{ fontSize: 12 }}>
                      <Text type="secondary">{t('common.lineLabel', { line: r.line })}</Text>
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
      <Card title={t('industryImport.batch.cardTitle')}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          {t('industryImport.batch.description')}
        </Text>
        <BatchManager />
      </Card>
    </Space>
  )
}

export default IndustryImportTab

// --- Batch Manager sub-component ---

const BatchManager: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
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
      message.error(getErrorMessage(e, t('industryImport.batch.loadFailed')))
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
        t('industryImport.batch.deleted', {
          links: res.data.links_deleted,
          talents: res.data.talents_deleted,
        })
      )
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
      await loadBatches(selectedPosition)
    } catch (e) {
      message.error(getErrorMessage(e, t('industryImport.batch.deleteFailed')))
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
      message.success(t('industryImport.batch.exported', { filename }))
    } catch (e) {
      message.error(getErrorMessage(e, t('industryImport.batch.exportFailed')))
    } finally {
      setExporting(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder={t('industryImport.batch.selectPlaceholder')}
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
            {t('industryImport.batch.exportAll')}
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
          locale={{ emptyText: t('industryImport.batch.empty') }}
          columns={[
            {
              title: t('industryImport.batch.columns.batch'),
              dataIndex: 'batch',
              key: 'batch',
              render: (v: string | null) => v ?? t('industryImport.batch.columns.noBatch'),
            },
            { title: t('industryImport.batch.columns.candidates'), dataIndex: 'count', key: 'count', width: 100 },
            {
              title: t('industryImport.batch.columns.time'),
              dataIndex: 'latest',
              key: 'latest',
              width: 180,
              render: (v: string | null) => (v ? v.slice(0, 19).replace('T', ' ') : '—'),
            },
            {
              title: t('industryImport.batch.columns.actions'),
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
                    {t('industryImport.batch.export')}
                  </Button>
                  <Popconfirm
                    title={t('industryImport.batch.deleteConfirmTitle')}
                    description={t('industryImport.batch.deleteConfirmDescription')}
                    okText={t('common.delete')}
                    cancelText={t('common.cancel')}
                    okButtonProps={{ danger: true }}
                    onConfirm={() => handleDelete(record.batch)}
                  >
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleting === (record.batch ?? '__none__')}
                    >
                      {t('common.delete')}
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
  const { t } = useTranslation(['systemConfig', 'common'])
  const navigate = useNavigate()

  return (
    <div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={t('industryImport.agentChannel.movedTitle')}
        description={
          <>
            {t('industryImport.agentChannel.movedDescriptionBefore')}
            <Text code>industry:write</Text>
            {t('industryImport.agentChannel.movedDescriptionAfter')}
          </>
        }
      />
      <Button
        type="primary"
        icon={<KeyOutlined />}
        onClick={() => navigate('/system-config?tab=api-keys')}
      >
        {t('industryImport.agentChannel.gotoApiKeys')}
      </Button>

      <Alert
        type="info"
        style={{ marginTop: 16 }}
        message={t('industryImport.agentChannel.exampleTitle')}
        description={
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              {t('industryImport.agentChannel.step1')}
            </Text>
            <pre style={{ margin: 0, fontSize: 12, overflow: 'auto' }}>
              {t('industryImport.agentChannel.step1Command', { origin: window.location.origin })}
            </pre>
            <Text type="secondary" style={{ display: 'block', margin: '12px 0 8px' }}>
              {t('industryImport.agentChannel.step2')}
            </Text>
            <pre style={{ margin: 0, fontSize: 12, overflow: 'auto' }}>
              {t('industryImport.agentChannel.step2Command', { origin: window.location.origin })}
            </pre>
          </>
        }
      />
    </div>
  )
}

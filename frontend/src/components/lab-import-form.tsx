import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Card,
  Typography,
  Space,
  Input,
  Button,
  Upload,
  Descriptions,
  Tag,
  Alert,
  Progress,
  message,
} from 'antd'
import { InboxOutlined, UploadOutlined, CloudSyncOutlined } from '@ant-design/icons'
import LabIcon from './lab-icon'
import type { UploadProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { getErrorMessage } from '../utils'

const { Dragger } = Upload
const { Text, Title } = Typography

const PREFETCH_LAB_KEY = 'lab_prefetch_lab'

export interface ImportReport {
  parent_lab: string
  total_lines: number
  total_parsed: number
  inserted: number
  skipped: number
  skip_reasons: { line: number; reason: string }[]
}

interface LabImportFormProps {
  onSuccess?: (report: ImportReport) => void
}

const LabImportForm: React.FC<LabImportFormProps> = ({ onSuccess }) => {
  const { t } = useTranslation('common')
  const [parentLab, setParentLab] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<ImportReport | null>(null)
  const [prefetchStatus, setPrefetchStatus] = useState<{
    status: string
    processed: number
    total: number
    current: string
    errors: number
    stale?: boolean
  } | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback((labName: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.lab.getPrefetchStatus(labName)
        setPrefetchStatus(res.data)
        if (
          res.data.status === 'completed' ||
          res.data.status === 'error' ||
          res.data.status === 'cancelled'
        ) {
          stopPolling()
          try {
            sessionStorage.removeItem(PREFETCH_LAB_KEY)
          } catch {
            // ignore
          }
        }
      } catch {
        // ignore poll errors
      }
    }, 3000)
  }, [stopPolling])

  // On mount: check if a prefetch is already running (e.g. after page switch)
  useEffect(() => {
    let cancelled = false
    async function checkRunning() {
      let labName: string | null = null
      try {
        labName = sessionStorage.getItem(PREFETCH_LAB_KEY)
      } catch {
        // ignore
      }
      if (!labName) return

      try {
        const res = await api.lab.getPrefetchStatus(labName)
        if (!cancelled && (res.data.status === 'running' || res.data.status === 'pending')) {
          setPrefetchStatus(res.data)
          startPolling(labName)
        }
      } catch {
        // ignore — no prior prefetch state
      }
    }
    checkRunning()
    return () => {
      cancelled = true
      stopPolling()
    }
  }, [startPolling, stopPolling])

  const beforeUpload: UploadProps['beforeUpload'] = file => {
    const isJsonl =
      file.name.endsWith('.jsonl') || file.type === 'application/jsonl' || file.type === ''
    if (!isJsonl) {
      message.error(t('labImport.jsonlOnly'))
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
    if (!selectedFile) {
      message.warning(t('labImport.selectFirst'))
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.lab.importUpload(selectedFile, parentLab.trim() || undefined)
      setReport(res.data as ImportReport)
      setSelectedFile(null)
      message.success(
        t('labImport.importDone', {
          inserted: res.data.inserted,
          skipped: res.data.skipped,
        })
      )
      onSuccess?.(res.data as ImportReport)

      // Auto-trigger homepage prefetch
      const labName = (res.data as ImportReport).parent_lab
      if (labName) {
        try {
          sessionStorage.setItem(PREFETCH_LAB_KEY, labName)
        } catch {
          // ignore
        }
        try {
          await api.lab.triggerPrefetch(labName)
          setPrefetchStatus({
            status: 'pending',
            processed: 0,
            total: 0,
            current: t('labImport.starting'),
            errors: 0,
          })
          startPolling(labName)
        } catch (e: unknown) {
          // 409 = already running — recover by polling existing progress
          const status = (e as { response?: { status?: number } }).response?.status
          if (status === 409) {
            try {
              const res = await api.lab.getPrefetchStatus(labName)
              setPrefetchStatus(res.data)
              if (res.data.status === 'running' || res.data.status === 'pending') {
                startPolling(labName)
              }
            } catch {
              // give up silently
            }
          }
          // other errors: prefetch not started, user can still use on-demand preview
        }
      }
    } catch (e) {
      message.error(getErrorMessage(e, t('labImport.importFailed')))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={5}>
          <LabIcon style={{ fontSize: 20, marginRight: 8 }} />
          {t('labImport.title')}
        </Title>
        <Text type="secondary">
          {t('labImport.subtitle')}
        </Text>

        <div style={{ marginTop: 16 }}>
          <Text strong>{t('labImport.labName')}</Text>
          <Input
            placeholder={t('labImport.labNamePlaceholder')}
            value={parentLab}
            onChange={e => setParentLab(e.target.value)}
            style={{ marginTop: 4, maxWidth: 400 }}
          />
          <Text type="secondary" style={{ display: 'block', fontSize: 12, marginTop: 4 }}>
            {t('labImport.labNameHint')}
          </Text>
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
            <p className="ant-upload-text">{t('labImport.dragText')}</p>
            <p className="ant-upload-hint">{t('labImport.hint')}</p>
          </Dragger>
        </div>

        <div style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            loading={uploading}
            onClick={handleImport}
            disabled={!selectedFile}
          >
            {t('labImport.start')}
          </Button>
        </div>
      </Card>

      {report && (
        <Card title={t('labImport.report')}>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label={t('labImport.fields.lab')}>{report.parent_lab}</Descriptions.Item>
            <Descriptions.Item label={t('labImport.fields.totalLines')}>{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label={t('labImport.fields.parsed')}>
              <Tag color="green">{report.total_parsed}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('labImport.fields.inserted')}>
              <Tag color="blue">{report.inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('labImport.fields.skipped')}>
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {report.skip_reasons.length > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={t('labImport.skipReasonsTitle', { count: report.skip_reasons.length })}
              description={
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  {report.skip_reasons.map((r, i) => (
                    <div key={i} style={{ fontSize: 12 }}>
                      <Text type="secondary">{t('labImport.line', { line: r.line })}</Text>
                      <Text>{r.reason}</Text>
                    </div>
                  ))}
                </div>
              }
            />
          )}
        </Card>
      )}

      {prefetchStatus && (
        <Card
          title={
            <Space>
              <CloudSyncOutlined spin={prefetchStatus.status === 'running'} />
              {t('labImport.prefetchTitle')}
            </Space>
          }
        >
          {prefetchStatus.status === 'pending' || prefetchStatus.status === 'running' ? (
            <>
              <Text type="secondary">
                {t('labImport.prefetchRunning', {
                  processed: prefetchStatus.processed,
                  total: prefetchStatus.total,
                })}
                {prefetchStatus.stale && t('labImport.prefetchStale')}
              </Text>
              {prefetchStatus.current &&
                prefetchStatus.current !== 'starting' &&
                prefetchStatus.current !== 'initializing' && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {t('labImport.prefetchCurrent', { current: prefetchStatus.current })}
                    </Text>
                  </div>
                )}
              <Progress
                percent={
                  prefetchStatus.total > 0
                    ? Math.round((prefetchStatus.processed / prefetchStatus.total) * 100)
                    : 0
                }
                status="active"
                style={{ marginTop: 12 }}
              />
            </>
          ) : prefetchStatus.status === 'completed' ? (
            <Alert
              type="success"
              showIcon
              message={`${t('labImport.prefetchDone', { total: prefetchStatus.total })}${
                prefetchStatus.errors > 0
                  ? t('labImport.prefetchDoneErrors', { count: prefetchStatus.errors })
                  : ''
              }`}
              description={t('labImport.prefetchDoneDesc')}
            />
          ) : prefetchStatus.status === 'error' ? (
            <Alert type="error" showIcon message={t('labImport.prefetchFailed')} />
          ) : prefetchStatus.status === 'cancelled' ? (
            <Alert type="warning" showIcon message={t('labImport.prefetchCancelled')} />
          ) : null}
        </Card>
      )}
    </Space>
  )
}

export default LabImportForm

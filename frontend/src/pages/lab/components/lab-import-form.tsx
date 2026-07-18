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
import LabIcon from '../../../components/lab-icon'
import type { UploadProps } from 'antd'
import { api } from '../../../services/api'
import { getErrorMessage } from '../../../utils'

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
      message.error('请上传 .jsonl 文件')
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
      message.warning('请先选择 JSONL 文件')
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.lab.importUpload(selectedFile, parentLab.trim() || undefined)
      setReport(res.data as ImportReport)
      setSelectedFile(null)
      message.success(`导入完成：${res.data.inserted} 人入库，${res.data.skipped} 行跳过`)
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
            current: '启动中...',
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
      message.error(getErrorMessage(e, '导入失败'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={5}>
          <LabIcon style={{ fontSize: 20, marginRight: 8 }} />
          AI 实验室人才导入
        </Title>
        <Text type="secondary">
          上传 ai-lab-talent-crawler 产出的 JSONL 文件，按实验室全量替换。
        </Text>

        <div style={{ marginTop: 16 }}>
          <Text strong>实验室名称（parent_lab）</Text>
          <Input
            placeholder="如：南京大学LAMDA实验室；若 JSONL 首行包含 lab 元数据则可留空"
            value={parentLab}
            onChange={e => setParentLab(e.target.value)}
            style={{ marginTop: 4, maxWidth: 400 }}
          />
          <Text type="secondary" style={{ display: 'block', fontSize: 12, marginTop: 4 }}>
            可选。当 JSONL 第一行包含 type=lab 的实验室元数据时会自动读取；填写时优先使用此处值
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
            <p className="ant-upload-text">点击或拖拽 JSONL 文件到此区域上传</p>
            <p className="ant-upload-hint">仅支持单个 .jsonl 文件（crawler 输出格式）</p>
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
            开始导入
          </Button>
        </div>
      </Card>

      {report && (
        <Card title="导入报告">
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="实验室">{report.parent_lab}</Descriptions.Item>
            <Descriptions.Item label="总行数">{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label="成功解析">
              <Tag color="green">{report.total_parsed}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="写入">
              <Tag color="blue">{report.inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="跳过">
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {report.skip_reasons.length > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={`${report.skip_reasons.length} 行被跳过（前 50 条）`}
              description={
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  {report.skip_reasons.map((r, i) => (
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

      {prefetchStatus && (
        <Card
          title={
            <Space>
              <CloudSyncOutlined spin={prefetchStatus.status === 'running'} />
              主页预抓取
            </Space>
          }
        >
          {prefetchStatus.status === 'pending' || prefetchStatus.status === 'running' ? (
            <>
              <Text type="secondary">
                正在批量抓取个人主页并缓存... ({prefetchStatus.processed}/{prefetchStatus.total})
                {prefetchStatus.stale && '（心跳超时，可重新触发）'}
              </Text>
              {prefetchStatus.current &&
                prefetchStatus.current !== 'starting' &&
                prefetchStatus.current !== 'initializing' && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前：{prefetchStatus.current}
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
              message={`预抓取完成：共 ${prefetchStatus.total} 人${
                prefetchStatus.errors > 0 ? `，${prefetchStatus.errors} 个失败` : ''
              }`}
              description={'个人主页已缓存，详情页的"加载预览"将秒开。'}
            />
          ) : prefetchStatus.status === 'error' ? (
            <Alert type="error" showIcon message="预抓取失败，请稍后重试" />
          ) : prefetchStatus.status === 'cancelled' ? (
            <Alert type="warning" showIcon message="预抓取已取消" />
          ) : null}
        </Card>
      )}
    </Space>
  )
}

export default LabImportForm

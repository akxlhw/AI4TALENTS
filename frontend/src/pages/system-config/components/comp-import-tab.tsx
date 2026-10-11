import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { UploadProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { InboxOutlined, TrophyOutlined, UploadOutlined } from '@ant-design/icons'
import { api } from '../../../services/api'
import type { CompImportReport } from '../../../services/api/competition'
import { getErrorMessage } from '../../../utils'
import '../../../i18n/namespaces/system-config'

const { Dragger } = Upload
const { Text, Title } = Typography

/**
 * Competition talent JSONL import tab (super_admin, system-config).
 * Upload one contest JSONL from comp-talent-crawler; results of that
 * contest are fully replaced in a single transaction on the backend.
 */
const CompImportTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<CompImportReport | null>(null)

  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    if (!file.name.endsWith('.jsonl')) {
      message.error(t('common.invalidJsonl'))
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
      message.warning(t('common.noFileSelected'))
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.comp.importUpload(selectedFile)
      setReport(res.data)
      setSelectedFile(null)
      message.success(
        t('compImport.importDone', {
          persons: res.data.persons_upserted,
          results: res.data.results_inserted,
          skipped: res.data.skipped,
        })
      )
    } catch (e) {
      message.error(getErrorMessage(e, t('common.importFailed')))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={5}>
          <TrophyOutlined style={{ marginRight: 8, color: 'var(--domain-secondary, #DD6B20)' }} />
          {t('compImport.heading')}
        </Title>
        <Text type="secondary">
          {t('compImport.description')}
        </Text>

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
            <p className="ant-upload-hint">{t('compImport.uploadHint')}</p>
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
            {t('common.startImport')}
          </Button>
        </div>
      </Card>

      {report && (
        <Card title={t('compImport.report.title')}>
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label={t('compImport.report.source')}>{report.source_code}</Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.contest')}>
              {report.contest_name}（{report.contest_external_id}）
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.totalLines')}>{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.persons')}>
              <Tag color="blue">{report.persons_upserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.teams')}>
              <Tag color="blue">{report.teams_upserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.resultsInserted')}>
              <Tag color="green">{report.results_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.resultsReplaced')}>
              <Tag color="orange">{report.results_deleted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.skipped')}>
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('compImport.report.duration')}>{report.duration_ms} ms</Descriptions.Item>
          </Descriptions>

          {report.skipped === 0 && report.results_inserted === 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message={t('compImport.report.noDataTitle')}
              description={t('compImport.report.noDataDescription')}
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
    </Space>
  )
}

export default CompImportTab

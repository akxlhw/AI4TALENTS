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
import { InboxOutlined, TrophyOutlined, UploadOutlined } from '@ant-design/icons'
import { api } from '../../../services/api'
import type { CompImportReport } from '../../../services/api/competition'
import { getErrorMessage } from '../../../utils'

const { Dragger } = Upload
const { Text, Title } = Typography

/**
 * Competition talent JSONL import tab (super_admin, system-config).
 * Upload one contest JSONL from comp-talent-crawler; results of that
 * contest are fully replaced in a single transaction on the backend.
 */
const CompImportTab: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<CompImportReport | null>(null)

  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    if (!file.name.endsWith('.jsonl')) {
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
      const res = await api.comp.importUpload(selectedFile)
      setReport(res.data)
      setSelectedFile(null)
      message.success(
        `导入完成：选手 ${res.data.persons_upserted} 人、成绩 ${res.data.results_inserted} 条入库，` +
          `${res.data.skipped} 行跳过`
      )
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
          <TrophyOutlined style={{ marginRight: 8, color: 'var(--domain-secondary, #DD6B20)' }} />
          竞赛人才导入
        </Title>
        <Text type="secondary">
          上传 comp-talent-crawler 产出的单场赛事 JSONL 文件（schema v1.0：
          meta → series → contest → team* → person*），该场赛事成绩将全量替换。
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
            <p className="ant-upload-text">点击或拖拽 JSONL 文件到此区域上传</p>
            <p className="ant-upload-hint">仅支持单个 .jsonl 文件（crawler 输出格式，≤ 20MB）</p>
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
            <Descriptions.Item label="数据源">{report.source_code}</Descriptions.Item>
            <Descriptions.Item label="赛事">
              {report.contest_name}（{report.contest_external_id}）
            </Descriptions.Item>
            <Descriptions.Item label="总行数">{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label="选手入库">
              <Tag color="blue">{report.persons_upserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="队伍入库">
              <Tag color="blue">{report.teams_upserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成绩新增">
              <Tag color="green">{report.results_inserted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成绩替换（删旧）">
              <Tag color="orange">{report.results_deleted}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="跳过">
              <Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">{report.duration_ms} ms</Descriptions.Item>
          </Descriptions>

          {report.skipped === 0 && report.results_inserted === 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message="未写入任何数据"
              description="文件中没有可导入的有效记录（空文件或全部行无效）。为保护既有数据，本次未做任何删除或写入。"
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
    </Space>
  )
}

export default CompImportTab

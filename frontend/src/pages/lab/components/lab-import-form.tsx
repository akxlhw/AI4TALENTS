import { useState } from 'react'
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
  message,
} from 'antd'
import { InboxOutlined, ExperimentOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { api } from '../../../services/api'
import { getErrorMessage } from '../../../utils'

const { Dragger } = Upload
const { Text, Title } = Typography

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
    if (!parentLab.trim()) {
      message.warning('请填写实验室名称')
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.lab.importUpload(selectedFile, parentLab.trim())
      setReport(res.data as ImportReport)
      setSelectedFile(null)
      message.success(`导入完成：${res.data.inserted} 人入库，${res.data.skipped} 行跳过`)
      onSuccess?.(res.data as ImportReport)
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
          <ExperimentOutlined style={{ marginRight: 8 }} />
          AI 实验室人才导入
        </Title>
        <Text type="secondary">
          上传 ai-lab-talent-crawler 产出的 JSONL 文件，按实验室全量替换。
        </Text>

        <div style={{ marginTop: 16 }}>
          <Text strong>实验室名称（parent_lab）</Text>
          <Input
            placeholder="如：Stanford AI Lab"
            value={parentLab}
            onChange={e => setParentLab(e.target.value)}
            style={{ marginTop: 4, maxWidth: 400 }}
          />
          <Text type="secondary" style={{ display: 'block', fontSize: 12, marginTop: 4 }}>
            必填，对应 labs.yaml 里的实验室 name；本次导入会替换该实验室的全部人才数据
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
            disabled={!selectedFile || !parentLab.trim()}
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
    </Space>
  )
}

export default LabImportForm

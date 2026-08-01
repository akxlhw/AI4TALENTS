import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { UploadProps } from 'antd'
import { BuildOutlined, InboxOutlined, UploadOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
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

          {report.total_parsed === 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message="未写入任何数据"
              description="文件中没有可导入的有效记录（空文件或全部行无效）。"
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

export default IndustryImportTab

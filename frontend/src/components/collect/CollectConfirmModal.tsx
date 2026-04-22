/**
 * CollectConfirmModal - 采集确认弹窗组件
 *
 * 职责：
 * - 显示采集范围信息
 * - 选择采集模式
 * - 确认启动采集
 */
import { Modal, Descriptions, Tag, Space, Radio, Tooltip } from 'antd'
import type { TechDomainCollect, VenueTypeConfig } from '../../types'

export interface CollectConfirmModalProps {
  visible: boolean
  domain: TechDomainCollect | null
  collectMode: string
  venueTypeMap: Record<string, VenueTypeConfig>
  onModeChange: (mode: string) => void
  onConfirm: () => void
  onCancel: () => void
}

const CollectConfirmModal: React.FC<CollectConfirmModalProps> = ({
  visible,
  domain,
  collectMode,
  venueTypeMap,
  onModeChange,
  onConfirm,
  onCancel,
}) => {
  return (
    <Modal
      title={`启动采集 - ${domain?.domain_name || ''}`}
      open={visible}
      onCancel={onCancel}
      onOk={onConfirm}
      okText="确认采集"
    >
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="采集范围">
          <Space size={[4, 4]} wrap>
            {(domain?.collect_sources || []).slice(0, 5).map(v => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={venueTypeMap[v.type]?.color || 'default'}>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {(domain?.collect_sources?.length || 0) > 5 && (
              <Tag>+{domain!.collect_sources!.length - 5}</Tag>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="数据类型">学者、论文、机构</Descriptions.Item>
        <Descriptions.Item label="时间范围">2020.1.1 至今</Descriptions.Item>
        <Descriptions.Item label="采集模式">
          <Radio.Group value={collectMode} onChange={(e) => onModeChange(e.target.value)}>
            <Radio.Button value="full">全量采集</Radio.Button>
            <Radio.Button value="incremental">增量采集</Radio.Button>
          </Radio.Group>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

export default CollectConfirmModal

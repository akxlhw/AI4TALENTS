/**
 * VenueConfigModal - 顶会顶刊配置弹窗组件
 *
 * 职责：
 * - 显示技术要素关联的顶会顶刊
 * - 使用 Transfer 组件进行选择
 * - 保存配置
 */
import { Modal, Alert, Typography, Transfer, Tag, Spin } from 'antd'
import type { TransferProps } from 'antd'
import type { VenueItem, VenueTypeConfig, TechElementCollect } from '../../types'

const { Text } = Typography

export interface VenueConfigModalProps {
  visible: boolean
  element: TechElementCollect | null
  allVenues: VenueItem[]
  selectedVenueIds: string[]
  loading: boolean
  venueTypeMap: Record<string, VenueTypeConfig>
  onSelectionChange: (targetKeys: string[]) => void
  onSave: () => void
  onCancel: () => void
}

interface TransferItem {
  key: string
  title: string
  description: string
  venue_type: string
}

const VenueConfigModal: React.FC<VenueConfigModalProps> = ({
  visible,
  element,
  allVenues,
  selectedVenueIds,
  loading,
  venueTypeMap,
  onSelectionChange,
  onSave,
  onCancel,
}) => {
  const dataSource: TransferItem[] = allVenues.map(v => ({
    key: String(v.venue_id),
    title: v.venue_name,
    description: v.venue_name_en || v.venue_code,
    venue_type: v.venue_type,
  }))

  const render: TransferProps['render'] = (item) => (
    <span>
      <Tag color={venueTypeMap[item.venue_type]?.color || 'default'} style={{ marginRight: 4 }}>
        {venueTypeMap[item.venue_type]?.label || item.venue_type}
      </Tag>
      {item.title}
      {item.description && <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>({item.description})</Text>}
    </span>
  )

  const filterOption: TransferProps['filterOption'] = (input, item) =>
    item.title?.toLowerCase().includes(input.toLowerCase()) ||
    item.description?.toLowerCase().includes(input.toLowerCase())

  return (
    <Modal
      title={`配置采集范围 - ${element?.element_name || ''}`}
      open={visible}
      onCancel={onCancel}
      onOk={onSave}
      width={800}
      okText="保存配置"
      confirmLoading={loading}
    >
      <div style={{ marginBottom: 16 }}>
        <Alert
          message="勾选需要采集的顶会顶刊，未勾选的将不会采集"
          type="info"
          showIcon
        />
        <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
          已关联 {allVenues.length} 个顶会顶刊，已选择 {selectedVenueIds.length} 个进行采集
        </Text>
      </div>
      <Spin spinning={loading}>
        <Transfer
          dataSource={dataSource}
          titles={['不采集', '待采集']}
          targetKeys={selectedVenueIds}
          onChange={(newTargetKeys) => onSelectionChange(newTargetKeys as string[])}
          render={render}
          listStyle={{
            width: 350,
            height: 400,
          }}
          showSearch
          filterOption={filterOption}
          locale={{
            itemUnit: '个',
            itemsUnit: '个',
            searchPlaceholder: '搜索...',
            notFoundContent: '该技术要素暂无关联的顶会顶刊',
          }}
        />
      </Spin>
    </Modal>
  )
}

export default VenueConfigModal

import { Modal, Typography, Tag, Alert, Spin, Transfer } from 'antd'
import { getVenueTypeConfig } from '../../../../constants'
import type { VenueItem, TechDomainCollect } from '../../../../types'

const { Text } = Typography

interface VenueConfigModalProps {
  open: boolean
  selectedDomain: TechDomainCollect | null
  allVenues: VenueItem[]
  selectedVenueIds: string[]
  venueLoading: boolean
  onSelectedVenueIdsChange: (ids: string[]) => void
  onCancel: () => void
  onOk: () => void
}

const VenueConfigModal: React.FC<VenueConfigModalProps> = ({
  open,
  selectedDomain,
  allVenues,
  selectedVenueIds,
  venueLoading,
  onSelectedVenueIdsChange,
  onCancel,
  onOk,
}) => {
  return (
    <Modal
      title={`配置采集范围 - ${selectedDomain?.domain_name || ''}`}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      width={800}
      okText="保存配置"
      confirmLoading={venueLoading}
    >
      <Alert message="勾选需要采集的顶会顶刊" type="info" showIcon style={{ marginBottom: 16 }} />
      <Spin spinning={venueLoading}>
        <Transfer
          dataSource={allVenues.map((v) => ({
            key: String(v.venue_id),
            title: (v.venue_code || v.venue_name).toUpperCase(),
            description: v.venue_name,
            venue_type: v.venue_type,
          }))}
          titles={['不采集', '待采集']}
          targetKeys={selectedVenueIds}
          onChange={(newTargetKeys) => onSelectedVenueIdsChange(newTargetKeys as string[])}
          render={(item) => (
            <span>
              <Tag color={getVenueTypeConfig(item.venue_type).color} style={{ marginRight: 4 }}>
                {getVenueTypeConfig(item.venue_type).label}
              </Tag>
              <Text strong>{item.title}</Text>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                ({item.description})
              </Text>
            </span>
          )}
          listStyle={{ width: 350, height: 400 }}
          showSearch
          locale={{
            itemUnit: '个',
            itemsUnit: '个',
            searchPlaceholder: '搜索...',
            notFoundContent: '暂无数据',
          }}
        />
      </Spin>
    </Modal>
  )
}

export default VenueConfigModal

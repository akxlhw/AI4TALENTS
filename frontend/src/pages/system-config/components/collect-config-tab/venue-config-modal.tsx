import { Modal, Typography, Tag, Alert, Spin, Transfer } from 'antd'
import { useTranslation } from 'react-i18next'
import { getVenueTypeConfig } from '../../../../constants'
import type { VenueItem, TechDomainCollect } from '../../../../types'
import '../../../../i18n/namespaces/system-config'

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
  const { t } = useTranslation(['systemConfig', 'common'])

  return (
    <Modal
      title={t('collectConfig.venueModal.title', {
        name: selectedDomain?.domain_name || '',
      })}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      width={800}
      okText={t('collectConfig.venueModal.saveConfig')}
      confirmLoading={venueLoading}
    >
      <Alert
        message={t('collectConfig.venueModal.selectHint')}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Spin spinning={venueLoading}>
        <Transfer
          dataSource={allVenues.map(v => ({
            key: String(v.venue_id),
            title: (v.venue_code || v.venue_name).toUpperCase(),
            description: v.venue_name,
            venue_type: v.venue_type,
          }))}
          titles={[t('collectConfig.venueModal.exclude'), t('collectConfig.venueModal.include')]}
          targetKeys={selectedVenueIds}
          onChange={newTargetKeys => onSelectedVenueIdsChange(newTargetKeys as string[])}
          render={item => (
            <span>
              <Tag color={getVenueTypeConfig(item.venue_type).color} style={{ marginRight: 4 }}>
                {t(`venueTypes.${item.venue_type}`, { defaultValue: item.venue_type })}
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
            itemUnit: t('collectConfig.venueModal.itemUnit'),
            itemsUnit: t('collectConfig.venueModal.itemsUnit'),
            searchPlaceholder: t('collectConfig.venueModal.searchPlaceholder'),
            notFoundContent: t('common:status.empty'),
          }}
        />
      </Spin>
    </Modal>
  )
}

export default VenueConfigModal

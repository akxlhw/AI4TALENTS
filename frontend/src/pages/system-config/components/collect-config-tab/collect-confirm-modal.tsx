import { Modal, Typography, Tag, Space, Tooltip, Descriptions, Select } from 'antd'
import { useTranslation } from 'react-i18next'
import { getCurrentYear, getVenueTypeConfig, TIME_RANGE_CONFIG } from '../../../../constants'
import '../../../../i18n/namespaces/system-config'
import type { TechDomainCollect } from '../../../../types'

const { Text } = Typography

interface CollectConfirmModalProps {
  open: boolean
  selectedDomain: TechDomainCollect | null
  startYear: number
  endYear: number | null
  onStartYearChange: (value: number) => void
  onEndYearChange: (value: number | null) => void
  onCancel: () => void
  onOk: () => void
}

const CollectConfirmModal: React.FC<CollectConfirmModalProps> = ({
  open,
  selectedDomain,
  startYear,
  endYear,
  onStartYearChange,
  onEndYearChange,
  onCancel,
  onOk,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  // Year options are generated here (instead of constants helpers) so the
  // labels can be translated; behavior mirrors getStartYearOptions/getEndYearOptions.
  const currentYear = getCurrentYear()
  const startYearOptions = []
  for (let y = currentYear; y >= TIME_RANGE_CONFIG.MIN_START_YEAR; y--) {
    startYearOptions.push({
      value: y,
      label: t('collectConfig.collectConfirm.yearOption', { year: y }),
    })
  }
  const endYearOptions: Array<{ value: number | null; label: string }> = [
    { value: null, label: t('collectConfig.collectConfirm.present') },
  ]
  for (let y = currentYear; y >= startYear; y--) {
    endYearOptions.push({
      value: y,
      label: t('collectConfig.collectConfirm.yearOption', { year: y }),
    })
  }

  return (
    <Modal
      title={t('collectConfig.collectConfirm.title', {
        name: selectedDomain?.domain_name || '',
      })}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      okText={t('collectConfig.collectConfirm.confirmCollect')}
    >
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={t('collectConfig.collectConfirm.scope')}>
          <Space size={[4, 4]} wrap>
            {(selectedDomain?.collect_sources || []).slice(0, 5).map(v => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {(selectedDomain?.collect_sources?.length || 0) > 5 && (
              <Tag>+{selectedDomain!.collect_sources!.length - 5}</Tag>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label={t('collectConfig.collectConfirm.dataType')}>
          {t('collectConfig.collectConfirm.dataTypeValue')}
        </Descriptions.Item>
        <Descriptions.Item label={t('collectConfig.collectConfirm.timeRange')}>
          <Space>
            <Select
              value={startYear}
              onChange={onStartYearChange}
              style={{ width: 120 }}
              options={startYearOptions}
            />
            <Text>{t('collectConfig.collectConfirm.to')}</Text>
            <Select
              value={endYear}
              onChange={onEndYearChange}
              style={{ width: 120 }}
              options={endYearOptions}
              placeholder={t('collectConfig.collectConfirm.present')}
            />
          </Space>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

export default CollectConfirmModal

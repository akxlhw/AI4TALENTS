import { Modal, Typography, Tag, Space, Tooltip, Descriptions, Select } from 'antd'
import { getVenueTypeConfig, getStartYearOptions, getEndYearOptions } from '../../../../constants'
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
  return (
    <Modal
      title={`启动采集 - ${selectedDomain?.domain_name || ''}`}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      okText="确认采集"
    >
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="采集范围">
          <Space size={[4, 4]} wrap>
            {(selectedDomain?.collect_sources || []).slice(0, 5).map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {(selectedDomain?.collect_sources?.length || 0) > 5 && (
              <Tag>+{selectedDomain!.collect_sources!.length - 5}</Tag>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="数据类型">学者、论文、机构</Descriptions.Item>
        <Descriptions.Item label="时间范围">
          <Space>
            <Select
              value={startYear}
              onChange={onStartYearChange}
              style={{ width: 120 }}
              options={getStartYearOptions()}
            />
            <Text>至</Text>
            <Select
              value={endYear}
              onChange={onEndYearChange}
              style={{ width: 120 }}
              options={getEndYearOptions(startYear)}
              placeholder="至今"
            />
          </Space>
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

export default CollectConfirmModal

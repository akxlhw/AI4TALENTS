import { Modal, Checkbox, Button, Space, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { ColumnConfig } from '../hooks/useColumnConfig'

const { Text } = Typography

interface ColumnSettingsProps {
  visible: boolean
  columns: ColumnConfig[]
  onToggle: (key: string) => void
  onReset: () => void
  onClose: () => void
}

const ColumnSettings: React.FC<ColumnSettingsProps> = ({
  visible,
  columns,
  onToggle,
  onReset,
  onClose,
}) => {
  const optionalColumns = columns.filter(col => !col.required)
  const visibleCount = columns.filter(col => col.visible).length

  return (
    <Modal
      title="列显示设置"
      open={visible}
      onCancel={onClose}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button icon={<ReloadOutlined />} onClick={onReset}>
            恢复默认
          </Button>
          <Button type="primary" onClick={onClose}>
            确定
          </Button>
        </Space>
      }
      width={400}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          选择要显示的列（已选择 {visibleCount} 列）
        </Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {columns.map(col => (
          <Checkbox
            key={col.key}
            checked={col.visible}
            disabled={col.required}
            onChange={() => onToggle(col.key)}
          >
            <Space>
              <span>{col.label}</span>
              {col.required && <Text type="secondary" style={{ fontSize: 12 }}>(固定)</Text>}
            </Space>
          </Checkbox>
        ))}
      </div>
    </Modal>
  )
}

export default ColumnSettings

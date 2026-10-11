import { Modal, Checkbox, Button, Space, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('common')
  const visibleCount = columns.filter(col => col.visible).length

  return (
    <Modal
      title={t('columnSettings.title')}
      open={visible}
      onCancel={onClose}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button icon={<ReloadOutlined />} onClick={onReset}>
            {t('columnSettings.reset')}
          </Button>
          <Button type="primary" onClick={onClose}>
            {t('actions.confirm')}
          </Button>
        </Space>
      }
      width={400}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          {t('columnSettings.hint', { count: visibleCount })}
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
              <span>{col.label.startsWith('common:') ? t(col.label) : col.label}</span>
              {col.required && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('columnSettings.required')}
                </Text>
              )}
            </Space>
          </Checkbox>
        ))}
      </div>
    </Modal>
  )
}

export default ColumnSettings

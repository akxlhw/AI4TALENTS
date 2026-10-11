import { useState } from 'react'
import { Modal, Checkbox, Typography, Space } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text, Paragraph } = Typography

interface ExportConfirmModalProps {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
}

const ExportConfirmModal: React.FC<ExportConfirmModalProps> = ({
  open,
  onConfirm,
  onCancel,
}) => {
  const { t } = useTranslation()
  const [checked, setChecked] = useState(false)

  const handleOk = () => {
    if (!checked) return
    onConfirm()
    setChecked(false)
  }

  const handleCancel = () => {
    onCancel()
    setChecked(false)
  }

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined style={{ color: '#faad14' }} />
          <span>{t('export.title')}</span>
        </Space>
      }
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      okText={t('export.confirm')}
      cancelText={t('actions.cancel')}
      okButtonProps={{ disabled: !checked }}
    >
      <Paragraph>
        {t('export.intro')}
      </Paragraph>
      <ul style={{ paddingLeft: 20, marginBottom: 16 }}>
        <li>
          <Text>{t('export.prohibitedContact')}</Text>
        </li>
        <li>
          <Text>{t('export.prohibitedThirdParty')}</Text>
        </li>
        <li>
          <Text>{t('export.prohibitedCommercial')}</Text>
        </li>
      </ul>
      <Paragraph type="danger">
        {t('export.warning')}
      </Paragraph>
      <Checkbox
        checked={checked}
        onChange={(e) => setChecked(e.target.checked)}
      >
        {t('export.acknowledge')}
      </Checkbox>
    </Modal>
  )
}

export default ExportConfirmModal

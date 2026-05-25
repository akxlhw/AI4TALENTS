import { useState } from 'react'
import { Modal, Checkbox, Typography, Space } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'

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
          <span>数据导出声明</span>
        </Space>
      }
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      okText="确认导出"
      cancelText="取消"
      okButtonProps={{ disabled: !checked }}
    >
      <Paragraph>
        您即将导出人才数据。根据《用户协议》，导出的数据仅限内部研究评估使用，严禁：
      </Paragraph>
      <ul style={{ paddingLeft: 20, marginBottom: 16 }}>
        <li>
          <Text>通过邮箱/电话等渠道向人才发起招聘联系</Text>
        </li>
        <li>
          <Text>将数据提供给第三方招聘机构</Text>
        </li>
        <li>
          <Text>将数据用于商业营销或数据贩卖</Text>
        </li>
      </ul>
      <Paragraph type="danger">
        违规使用将导致账号封禁及法律责任。
      </Paragraph>
      <Checkbox
        checked={checked}
        onChange={(e) => setChecked(e.target.checked)}
      >
        我已阅读并承诺遵守上述限制
      </Checkbox>
    </Modal>
  )
}

export default ExportConfirmModal

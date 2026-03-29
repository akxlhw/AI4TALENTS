/**
 * CreatePoolModal - 创建人才池弹窗组件
 */
import { Modal, Input, Typography } from 'antd'

const { Text } = Typography

export interface CreatePoolModalProps {
  visible: boolean
  poolName: string
  poolDesc: string
  loading: boolean
  onNameChange: (name: string) => void
  onDescChange: (desc: string) => void
  onOk: () => void
  onCancel: () => void
}

const CreatePoolModal: React.FC<CreatePoolModalProps> = ({
  visible,
  poolName,
  poolDesc,
  loading,
  onNameChange,
  onDescChange,
  onOk,
  onCancel,
}) => {
  return (
    <Modal
      title="创建人才池"
      open={visible}
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={loading}
      okText="创建"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">人才池可以帮助您分类管理关注的候选人</Text>
      </div>
      <Input
        placeholder="人才池名称"
        value={poolName}
        onChange={(e) => onNameChange(e.target.value)}
        style={{ marginBottom: 12 }}
      />
      <Input.TextArea
        placeholder="描述（可选）"
        value={poolDesc}
        onChange={(e) => onDescChange(e.target.value)}
        rows={3}
      />
    </Modal>
  )
}

export default CreatePoolModal

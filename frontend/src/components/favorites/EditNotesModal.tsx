/**
 * EditNotesModal - 编辑备注弹窗组件
 */
import { Modal, Input } from 'antd'
import type { FavoriteTalent } from '../../types'

export interface EditNotesModalProps {
  visible: boolean
  favorite: FavoriteTalent | null
  notes: string
  loading: boolean
  onNotesChange: (notes: string) => void
  onOk: () => void
  onCancel: () => void
}

const EditNotesModal: React.FC<EditNotesModalProps> = ({
  visible,
  favorite,
  notes,
  loading,
  onNotesChange,
  onOk,
  onCancel,
}) => {
  return (
    <Modal
      title="编辑备注"
      open={visible}
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={loading}
      okText="保存"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ marginBottom: 8 }}>
          <strong>候选人：</strong>{favorite?.name}
        </p>
        <Input.TextArea
          rows={4}
          placeholder="记录关注该候选人的原因..."
          value={notes}
          onChange={(e) => onNotesChange(e.target.value)}
          maxLength={500}
          showCount
        />
      </div>
    </Modal>
  )
}

export default EditNotesModal

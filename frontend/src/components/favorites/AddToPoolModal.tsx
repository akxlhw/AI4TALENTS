/**
 * AddToPoolModal - 加入人才池弹窗组件
 */
import { Modal, Select, Typography } from 'antd'
import type { FavoriteTalent, TalentPool } from '../../types'

const { Text } = Typography

export interface AddToPoolModalProps {
  visible: boolean
  favorite: FavoriteTalent | null
  pools: TalentPool[]
  selectedPoolId: number | undefined
  onPoolChange: (poolId: number) => void
  onOk: () => void
  onCancel: () => void
}

const AddToPoolModal: React.FC<AddToPoolModalProps> = ({
  visible,
  favorite,
  pools,
  selectedPoolId,
  onPoolChange,
  onOk,
  onCancel,
}) => {
  return (
    <Modal
      title="加入人才池"
      open={visible}
      onOk={onOk}
      onCancel={onCancel}
      okText="加入"
      cancelText="取消"
      okButtonProps={{ disabled: !selectedPoolId }}
    >
      <div style={{ marginBottom: 16 }}>
        <Text>将 <strong>{favorite?.name}</strong> 加入人才池：</Text>
      </div>
      <Select
        placeholder="选择人才池"
        value={selectedPoolId}
        onChange={onPoolChange}
        style={{ width: '100%' }}
        options={pools.map(p => ({
          value: p.pool_id,
          label: `${p.pool_name} (${p.member_count}人)`
        }))}
      />
      {pools.length === 0 && (
        <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
          暂无人才池，请先创建
        </Text>
      )}
    </Modal>
  )
}

export default AddToPoolModal

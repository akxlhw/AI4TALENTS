import { useEffect, useState } from 'react'
import { Input, Modal, Select, Typography, message } from 'antd'
import { api } from '../../../services/api'
import type { FavoriteTalent, TalentPool } from '../../../types'

const { Text } = Typography

interface EditNotesModalProps {
  favorite: FavoriteTalent | null
  open: boolean
  onCancel: () => void
  onSaved: (favoriteId: number, notes: string) => void
}

export const EditNotesModal: React.FC<EditNotesModalProps> = ({
  favorite,
  open,
  onCancel,
  onSaved,
}) => {
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) setNotes(favorite?.notes || '')
  }, [open, favorite])

  const handleSave = async () => {
    if (!favorite) return

    setSaving(true)
    try {
      await api.favorites.update(favorite.talent_id, notes)
      onSaved(favorite.favorite_id, notes)
      message.success('备注已更新')
    } catch {
      message.error('更新备注失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="编辑备注"
      open={open}
      onOk={handleSave}
      onCancel={onCancel}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ marginBottom: 8 }}>
          <strong>候选人：</strong>
          {favorite?.name}
        </p>
        <Input.TextArea
          rows={4}
          placeholder="记录关注该候选人的原因..."
          value={notes}
          onChange={e => setNotes(e.target.value)}
          maxLength={500}
          showCount
        />
      </div>
    </Modal>
  )
}

interface CreatePoolModalProps {
  open: boolean
  onCancel: () => void
  onCreated: () => void
}

export const CreatePoolModal: React.FC<CreatePoolModalProps> = ({ open, onCancel, onCreated }) => {
  const [poolName, setPoolName] = useState('')
  const [poolDesc, setPoolDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const resetFields = () => {
    setPoolName('')
    setPoolDesc('')
  }

  const handleCreate = async () => {
    if (!poolName.trim()) {
      message.warning('请输入人才池名称')
      return
    }

    setCreating(true)
    try {
      await api.talentPools.create({
        pool_name: poolName.trim(),
        scope_desc: poolDesc || undefined,
      })
      message.success('人才池已创建')
      resetFields()
      onCreated()
    } catch {
      message.error('创建失败')
    } finally {
      setCreating(false)
    }
  }

  return (
    <Modal
      title="创建人才池"
      open={open}
      onOk={handleCreate}
      onCancel={() => {
        resetFields()
        onCancel()
      }}
      confirmLoading={creating}
      okText="创建"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">人才池可以帮助您分类管理关注的候选人</Text>
      </div>
      <Input
        placeholder="人才池名称"
        value={poolName}
        onChange={e => setPoolName(e.target.value)}
        style={{ marginBottom: 12 }}
      />
      <Input.TextArea
        placeholder="描述（可选）"
        value={poolDesc}
        onChange={e => setPoolDesc(e.target.value)}
        rows={3}
      />
    </Modal>
  )
}

interface AddToPoolModalProps {
  favorite: FavoriteTalent | null
  pools: TalentPool[]
  open: boolean
  onClose: () => void
}

export const AddToPoolModal: React.FC<AddToPoolModalProps> = ({
  favorite,
  pools,
  open,
  onClose,
}) => {
  const [selectedPoolId, setSelectedPoolId] = useState<number | undefined>()

  const handleClose = () => {
    setSelectedPoolId(undefined)
    onClose()
  }

  const handleAdd = async () => {
    if (!selectedPoolId || !favorite) return

    try {
      await api.talentPools.addMember(selectedPoolId, favorite.talent_id)
      message.success('已加入人才池')
      handleClose()
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message.warning(axiosError.response.data.detail)
      } else {
        message.error('加入失败')
      }
    }
  }

  return (
    <Modal
      title="加入人才池"
      open={open}
      onOk={handleAdd}
      onCancel={handleClose}
      okText="加入"
      cancelText="取消"
      okButtonProps={{ disabled: !selectedPoolId }}
    >
      <div style={{ marginBottom: 16 }}>
        <Text>
          将 <strong>{favorite?.name}</strong> 加入人才池：
        </Text>
      </div>
      <Select
        placeholder="选择人才池"
        value={selectedPoolId}
        onChange={setSelectedPoolId}
        style={{ width: '100%' }}
        options={pools.map(p => ({
          value: p.pool_id,
          label: `${p.pool_name} (${p.member_count}人)`,
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

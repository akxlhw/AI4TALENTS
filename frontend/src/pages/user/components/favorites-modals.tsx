import { useEffect, useState } from 'react'
import { Input, Modal, Select, Typography, message } from 'antd'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation(['user', 'common'])
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
      message.success(t('user:notesModal.saved'))
    } catch {
      message.error(t('user:notesModal.saveFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={t('user:notesModal.title')}
      open={open}
      onOk={handleSave}
      onCancel={onCancel}
      confirmLoading={saving}
      okText={t('user:notesModal.save')}
      cancelText={t('common:actions.cancel')}
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ marginBottom: 8 }}>
          <strong>{t('user:notesModal.candidate')}</strong>
          {favorite?.name}
        </p>
        <Input.TextArea
          rows={4}
          placeholder={t('user:notesModal.placeholder')}
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
  const { t } = useTranslation(['user', 'common'])
  const [poolName, setPoolName] = useState('')
  const [poolDesc, setPoolDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const resetFields = () => {
    setPoolName('')
    setPoolDesc('')
  }

  const handleCreate = async () => {
    if (!poolName.trim()) {
      message.warning(t('user:createPool.nameRequired'))
      return
    }

    setCreating(true)
    try {
      await api.talentPools.create({
        pool_name: poolName.trim(),
        scope_desc: poolDesc || undefined,
      })
      message.success(t('user:createPool.success'))
      resetFields()
      onCreated()
    } catch {
      message.error(t('user:createPool.failed'))
    } finally {
      setCreating(false)
    }
  }

  return (
    <Modal
      title={t('user:createPool.title')}
      open={open}
      onOk={handleCreate}
      onCancel={() => {
        resetFields()
        onCancel()
      }}
      confirmLoading={creating}
      okText={t('user:createPool.confirm')}
      cancelText={t('common:actions.cancel')}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">{t('user:createPool.hint')}</Text>
      </div>
      <Input
        placeholder={t('user:createPool.namePlaceholder')}
        value={poolName}
        onChange={e => setPoolName(e.target.value)}
        style={{ marginBottom: 12 }}
      />
      <Input.TextArea
        placeholder={t('user:createPool.descPlaceholder')}
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
  const { t } = useTranslation(['user', 'common'])
  const [selectedPoolId, setSelectedPoolId] = useState<number | undefined>()

  const handleClose = () => {
    setSelectedPoolId(undefined)
    onClose()
  }

  const handleAdd = async () => {
    if (!selectedPoolId || !favorite) return

    try {
      await api.talentPools.addMember(selectedPoolId, favorite.talent_id)
      message.success(t('user:addToPool.success'))
      handleClose()
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message.warning(axiosError.response.data.detail)
      } else {
        message.error(t('user:addToPool.failed'))
      }
    }
  }

  return (
    <Modal
      title={t('user:addToPool.title')}
      open={open}
      onOk={handleAdd}
      onCancel={handleClose}
      okText={t('user:addToPool.confirm')}
      cancelText={t('common:actions.cancel')}
      okButtonProps={{ disabled: !selectedPoolId }}
    >
      <div style={{ marginBottom: 16 }}>
        <Text>
          {t('user:addToPool.introBefore')}
          <strong>{favorite?.name}</strong>
          {t('user:addToPool.introAfter')}
        </Text>
      </div>
      <Select
        placeholder={t('user:addToPool.poolPlaceholder')}
        value={selectedPoolId}
        onChange={setSelectedPoolId}
        style={{ width: '100%' }}
        options={pools.map(p => ({
          value: p.pool_id,
          label: t('user:addToPool.poolOption', { name: p.pool_name, count: p.member_count }),
        }))}
      />
      {pools.length === 0 && (
        <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
          {t('user:addToPool.empty')}
        </Text>
      )}
    </Modal>
  )
}

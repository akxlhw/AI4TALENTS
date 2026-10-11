import React, { useState } from 'react'
import { Button, Modal, Input, Tooltip } from 'antd'
import { StarOutlined, StarFilled } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useFavorites } from '../contexts/FavoritesContext'

interface FavoriteButtonProps {
  talentId: number
  size?: 'small' | 'middle' | 'large'
  showText?: boolean
  onFavoriteChange?: (isFavorited: boolean) => void
}

const FavoriteButton: React.FC<FavoriteButtonProps> = ({
  talentId,
  size = 'middle',
  showText = false,
  onFavoriteChange,
}) => {
  const { t } = useTranslation('common')
  const { isFavorited, addFavorite, removeFavorite } = useFavorites()
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [notes, setNotes] = useState('')

  const favorited = isFavorited(talentId)

  const handleClick = () => {
    if (favorited) {
      // Show confirmation before removing
      Modal.confirm({
        title: t('favorite.removeTitle'),
        content: t('favorite.removeConfirm'),
        okText: t('actions.confirm'),
        cancelText: t('actions.cancel'),
        onOk: handleRemove,
      })
    } else {
      // Show modal to add notes
      setModalVisible(true)
    }
  }

  const handleRemove = async () => {
    setLoading(true)
    try {
      await removeFavorite(talentId)
      onFavoriteChange?.(false)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async () => {
    setLoading(true)
    try {
      await addFavorite(talentId, notes || undefined)
      setModalVisible(false)
      setNotes('')
      onFavoriteChange?.(true)
    } catch {
      // Error already handled in context
    } finally {
      setLoading(false)
    }
  }

  const handleModalCancel = () => {
    setModalVisible(false)
    setNotes('')
  }

  if (favorited) {
    return (
      <Tooltip title={t('favorite.addedTooltip')}>
        <Button
          type="primary"
          ghost
          icon={<StarFilled />}
          size={size}
          loading={loading}
          onClick={handleClick}
        >
          {showText && t('favorite.addedLabel')}
        </Button>
      </Tooltip>
    )
  }

  return (
    <>
      <Tooltip title={t('favorite.addTooltip')}>
        <Button
          icon={<StarOutlined />}
          size={size}
          loading={loading}
          onClick={handleClick}
        >
          {showText && t('favorite.addLabel')}
        </Button>
      </Tooltip>

      <Modal
        title={t('favorite.addTitle')}
        open={modalVisible}
        onOk={handleAdd}
        onCancel={handleModalCancel}
        confirmLoading={loading}
        okText={t('actions.confirm')}
        cancelText={t('actions.cancel')}
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ marginBottom: 8, color: '#666' }}>
            {t('favorite.notesHint')}
          </p>
          <Input.TextArea
            rows={4}
            placeholder={t('favorite.notesPlaceholder')}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={500}
            showCount
          />
        </div>
      </Modal>
    </>
  )
}

export default FavoriteButton

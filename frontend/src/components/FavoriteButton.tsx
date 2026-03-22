import React, { useState } from 'react'
import { Button, Modal, Input, Tooltip } from 'antd'
import { StarOutlined, StarFilled } from '@ant-design/icons'
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
  const { isFavorited, addFavorite, removeFavorite } = useFavorites()
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [notes, setNotes] = useState('')

  const favorited = isFavorited(talentId)

  const handleClick = () => {
    if (favorited) {
      // Show confirmation before removing
      Modal.confirm({
        title: '取消收藏',
        content: '确定要取消收藏该候选人吗？',
        okText: '确定',
        cancelText: '取消',
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
      <Tooltip title="已收藏，点击取消">
        <Button
          type="primary"
          ghost
          icon={<StarFilled />}
          size={size}
          loading={loading}
          onClick={handleClick}
        >
          {showText && '已收藏'}
        </Button>
      </Tooltip>
    )
  }

  return (
    <>
      <Tooltip title="添加收藏">
        <Button
          icon={<StarOutlined />}
          size={size}
          loading={loading}
          onClick={handleClick}
        >
          {showText && '收藏'}
        </Button>
      </Tooltip>

      <Modal
        title="添加收藏"
        open={modalVisible}
        onOk={handleAdd}
        onCancel={handleModalCancel}
        confirmLoading={loading}
        okText="确定"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ marginBottom: 8, color: '#666' }}>
            可以添加备注记录关注该候选人的原因（可选）
          </p>
          <Input.TextArea
            rows={4}
            placeholder="例如：研究方向匹配、学术背景优秀等..."
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

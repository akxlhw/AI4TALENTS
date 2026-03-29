/**
 * 我的收藏页面 (重构版)
 *
 * 已拆分的组件:
 * - FavoriteTalentTable: 收藏人才表格
 * - TalentPoolSection: 人才池区域
 * - EditNotesModal: 编辑备注弹窗
 * - CreatePoolModal: 创建人才池弹窗
 * - AddToPoolModal: 加入人才池弹窗
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Typography, Tabs, message, Modal } from 'antd'
import { StarFilled, FolderOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import TalentCompareModal from '../components/TalentCompareModal'
import type { FavoriteTalent, TalentPool, FollowupStatus } from '../types'
import {
  FavoriteTalentTable,
  TalentPoolSection,
  EditNotesModal,
  CreatePoolModal,
  AddToPoolModal,
} from '../components/favorites'

const { Title } = Typography

const FavoritesPageRefactored: React.FC = () => {
  const navigate = useNavigate()

  // Favorites state
  const [favorites, setFavorites] = useState<FavoriteTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const pageSize = 20

  // Filters
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [followupFilter, setFollowupFilter] = useState<string | undefined>()

  // Talent pools
  const [pools, setPools] = useState<TalentPool[]>([])
  const [poolsLoading, setPoolsLoading] = useState(false)

  // Followup statuses
  const [followupStatuses, setFollowupStatuses] = useState<FollowupStatus[]>([])

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)

  // Compare state
  const [compareModalVisible, setCompareModalVisible] = useState(false)

  // Active tab
  const [activeTab, setActiveTab] = useState('favorites')

  // Edit notes modal
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingFavorite, setEditingFavorite] = useState<FavoriteTalent | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [editLoading, setEditLoading] = useState(false)

  // Create pool modal
  const [createPoolModalVisible, setCreatePoolModalVisible] = useState(false)
  const [newPoolName, setNewPoolName] = useState('')
  const [newPoolDesc, setNewPoolDesc] = useState('')
  const [createPoolLoading, setCreatePoolLoading] = useState(false)

  // Add to pool modal
  const [addToPoolModalVisible, setAddToPoolModalVisible] = useState(false)
  const [addingToPoolFavorite, setAddingToPoolFavorite] = useState<FavoriteTalent | null>(null)
  const [selectedPoolId, setSelectedPoolId] = useState<number | undefined>()

  useEffect(() => {
    loadFavorites()
    loadPools()
    loadFollowupStatuses()
  }, [page, roleFilter, keyword, followupFilter])

  const loadFavorites = async () => {
    setLoading(true)
    try {
      const response = await api.favorites.list({
        page,
        page_size: pageSize,
        role_type: roleFilter,
        keyword: keyword || undefined,
      })
      setFavorites(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      console.error('Failed to load favorites:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadPools = async () => {
    setPoolsLoading(true)
    try {
      const response = await api.talentPools.list()
      setPools(response.data.items || [])
    } catch (error) {
      console.error('Failed to load pools:', error)
    } finally {
      setPoolsLoading(false)
    }
  }

  const loadFollowupStatuses = async () => {
    try {
      const response = await api.talentPools.getFollowupStatuses()
      setFollowupStatuses(response.data || [])
    } catch (error) {
      console.error('Failed to load followup statuses:', error)
    }
  }

  // Filter handlers
  const handleSearch = () => {
    setPage(1)
    loadFavorites()
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setKeyword('')
    setFollowupFilter(undefined)
    setPage(1)
  }

  // Favorite operations
  const handleEditNotes = (record: FavoriteTalent) => {
    setEditingFavorite(record)
    setEditNotes(record.notes || '')
    setEditModalVisible(true)
  }

  const handleSaveNotes = async () => {
    if (!editingFavorite) return

    setEditLoading(true)
    try {
      await api.favorites.update(editingFavorite.talent_id, editNotes)
      setFavorites(prev => prev.map(f =>
        f.favorite_id === editingFavorite.favorite_id
          ? { ...f, notes: editNotes }
          : f
      ))
      setEditModalVisible(false)
      message.success('备注已更新')
    } catch (error) {
      message.error('更新备注失败')
    } finally {
      setEditLoading(false)
    }
  }

  const handleRemoveFavorite = (record: FavoriteTalent) => {
    Modal.confirm({
      title: '取消收藏',
      content: `确定要取消收藏 "${record.name}" 吗？`,
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.favorites.remove(record.talent_id)
          setFavorites(prev => prev.filter(f => f.favorite_id !== record.favorite_id))
          setTotal(prev => prev - 1)
          message.success('已取消收藏')
        } catch (error) {
          message.error('取消收藏失败')
        }
      },
    })
  }

  const handleUpdateFollowupStatus = async (talentId: number, status: string) => {
    try {
      await api.talentPools.updateFollowupStatus(talentId, status)
      setFavorites(prev => prev.map(f =>
        f.talent_id === talentId ? { ...f, followup_status: status } : f
      ))
      message.success('跟进状态已更新')
    } catch (error) {
      message.error('更新失败')
    }
  }

  // Pool operations
  const handleCreatePool = async () => {
    if (!newPoolName.trim()) {
      message.warning('请输入人才池名称')
      return
    }

    setCreatePoolLoading(true)
    try {
      await api.talentPools.create({
        pool_name: newPoolName.trim(),
        scope_desc: newPoolDesc || undefined,
      })
      message.success('人才池已创建')
      setCreatePoolModalVisible(false)
      setNewPoolName('')
      setNewPoolDesc('')
      loadPools()
    } catch (error) {
      message.error('创建失败')
    } finally {
      setCreatePoolLoading(false)
    }
  }

  const handleAddToPool = async () => {
    if (!selectedPoolId || !addingToPoolFavorite) return

    try {
      await api.talentPools.addMember(selectedPoolId, addingToPoolFavorite.talent_id)
      message.success('已加入人才池')
      setAddToPoolModalVisible(false)
      setSelectedPoolId(undefined)
      setAddingToPoolFavorite(null)
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } }
        if (axiosError.response?.data?.detail) {
          message.warning(axiosError.response.data.detail)
          return
        }
      }
      message.error('加入失败')
    }
  }

  // Export
  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的候选人')
      return
    }

    setExporting(true)
    try {
      const talentIds = favorites
        .filter(f => selectedRowKeys.includes(f.favorite_id))
        .map(f => f.talent_id)

      const response = await api.talents.export(talentIds, format)
      const blob = new Blob([response.data], {
        type: format === 'xlsx'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'text/csv'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `favorites_export.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success(`已导出 ${selectedRowKeys.length} 位候选人`)
    } catch (error) {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  // Compare
  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning('请选择2-4位候选人进行对比')
      return
    }
    setCompareModalVisible(true)
  }

  const selectedTalentIds = favorites
    .filter(f => selectedRowKeys.includes(f.favorite_id))
    .map(f => f.talent_id)

  return (
    <div>
      <Title level={3}>
        <StarFilled style={{ marginRight: 8, color: '#faad14' }} />
        我的收藏
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'favorites',
            label: (
              <span>
                <StarFilled /> 收藏列表
              </span>
            ),
            children: (
              <Card>
                <FavoriteTalentTable
                  data={favorites}
                  loading={loading}
                  total={total}
                  page={page}
                  pageSize={pageSize}
                  selectedKeys={selectedRowKeys}
                  followupStatuses={followupStatuses}
                  roleFilter={roleFilter}
                  keyword={keyword}
                  followupFilter={followupFilter}
                  onSelectChange={setSelectedRowKeys}
                  onPageChange={setPage}
                  onSearch={handleSearch}
                  onResetFilters={handleResetFilters}
                  onRoleFilterChange={(val) => { setRoleFilter(val); setPage(1) }}
                  onKeywordChange={setKeyword}
                  onFollowupFilterChange={(val) => { setFollowupFilter(val); setPage(1) }}
                  onEditNotes={handleEditNotes}
                  onRemoveFavorite={handleRemoveFavorite}
                  onUpdateFollowupStatus={handleUpdateFollowupStatus}
                  onAddToPool={(record) => {
                    setAddingToPoolFavorite(record)
                    setAddToPoolModalVisible(true)
                  }}
                  onTalentClick={(id) => navigate(`/talents/${id}`)}
                  onSchoolClick={(id) => navigate(`/schools/${id}`)}
                  onExport={handleExport}
                  onCompare={handleCompare}
                  exporting={exporting}
                />
              </Card>
            ),
          },
          {
            key: 'pools',
            label: (
              <span>
                <FolderOutlined /> 人才池
              </span>
            ),
            children: (
              <Card>
                <TalentPoolSection
                  pools={pools}
                  loading={poolsLoading}
                  onCreatePool={() => setCreatePoolModalVisible(true)}
                  onPoolClick={(id) => navigate(`/pools/${id}`)}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Compare Modal */}
      <TalentCompareModal
        visible={compareModalVisible}
        talentIds={selectedTalentIds}
        onClose={() => setCompareModalVisible(false)}
      />

      {/* Edit Notes Modal */}
      <EditNotesModal
        visible={editModalVisible}
        favorite={editingFavorite}
        notes={editNotes}
        loading={editLoading}
        onNotesChange={setEditNotes}
        onOk={handleSaveNotes}
        onCancel={() => setEditModalVisible(false)}
      />

      {/* Create Pool Modal */}
      <CreatePoolModal
        visible={createPoolModalVisible}
        poolName={newPoolName}
        poolDesc={newPoolDesc}
        loading={createPoolLoading}
        onNameChange={setNewPoolName}
        onDescChange={setNewPoolDesc}
        onOk={handleCreatePool}
        onCancel={() => {
          setCreatePoolModalVisible(false)
          setNewPoolName('')
          setNewPoolDesc('')
        }}
      />

      {/* Add to Pool Modal */}
      <AddToPoolModal
        visible={addToPoolModalVisible}
        favorite={addingToPoolFavorite}
        pools={pools}
        selectedPoolId={selectedPoolId}
        onPoolChange={setSelectedPoolId}
        onOk={handleAddToPool}
        onCancel={() => {
          setAddToPoolModalVisible(false)
          setSelectedPoolId(undefined)
          setAddingToPoolFavorite(null)
        }}
      />
    </div>
  )
}

export default FavoritesPageRefactored

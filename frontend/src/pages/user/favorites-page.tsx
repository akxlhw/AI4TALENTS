import { useCallback, useEffect, useState } from 'react'
import { logger } from '../../utils/logger'
import { useAuth } from '../../contexts/AuthContext'
import { useTranslation } from 'react-i18next'
import { Modal, Tabs, Typography, message, type TablePaginationConfig } from 'antd'
import { FolderOutlined, StarFilled } from '@ant-design/icons'
import { api } from '../../services/api'
import TalentCompareModal from '../../components/TalentCompareModal'
import ExportConfirmModal from '../../components/ExportConfirmModal'
import { semanticColors } from '../../theme'
import { useExportDownload } from '../../hooks/useExportDownload'
import { i18n } from '../../i18n'
import '../../i18n/namespaces/user'
import type { FavoriteTalent, TalentPool, FollowupStatus } from '../../types'
import FavoritesFilterBar from './components/favorites-filter-bar'
import FavoritesTableCard from './components/favorites-table-card'
import TalentPoolTab from './components/talent-pool-tab'
import { useFavoriteColumns } from './components/favorites-columns'
import { AddToPoolModal, CreatePoolModal, EditNotesModal } from './components/favorites-modals'

const { Title } = Typography

const FavoritesPage: React.FC = () => {
  const { t } = useTranslation(['user', 'common'])
  const { isAdmin } = useAuth()
  const [loading, setLoading] = useState(true)
  const [favorites, setFavorites] = useState<FavoriteTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Filters
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [followupFilter, setFollowupFilter] = useState<string | undefined>()

  // Talent pools
  const [pools, setPools] = useState<TalentPool[]>([])
  const [poolsLoading, setPoolsLoading] = useState(false)
  const [createPoolModalVisible, setCreatePoolModalVisible] = useState(false)

  // Followup statuses
  const [followupStatuses, setFollowupStatuses] = useState<FollowupStatus[]>([])

  // Edit notes modal
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingFavorite, setEditingFavorite] = useState<FavoriteTalent | null>(null)

  // Add to pool modal
  const [addToPoolModalVisible, setAddToPoolModalVisible] = useState(false)
  const [addingToPoolFavorite, setAddingToPoolFavorite] = useState<FavoriteTalent | null>(null)

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])

  // Compare state
  const [compareModalVisible, setCompareModalVisible] = useState(false)

  // Active tab
  const [activeTab, setActiveTab] = useState('favorites')

  const loadFavorites = useCallback(async () => {
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
    } catch {
      logger.error('Operation failed')
      // Direct instance call keeps this callback's deps stable across language switches
      message.error(i18n.t('user:favorites.loadFailed', { ns: 'user' }))
    } finally {
      setLoading(false)
    }
  }, [page, roleFilter, keyword])

  const loadPools = useCallback(async () => {
    setPoolsLoading(true)
    try {
      const response = await api.talentPools.list()
      setPools(response.data.items || [])
    } catch {
      logger.error('Operation failed')
      message.error(i18n.t('user:pools.loadFailed', { ns: 'user' }))
    } finally {
      setPoolsLoading(false)
    }
  }, [])

  const loadFollowupStatuses = useCallback(async () => {
    try {
      const response = await api.talentPools.getFollowupStatuses()
      setFollowupStatuses(response.data || [])
    } catch {
      logger.error('Operation failed')
      message.error(i18n.t('user:followup.loadFailed', { ns: 'user' }))
    }
  }, [])

  useEffect(() => {
    loadFavorites()
    loadPools()
    loadFollowupStatuses()
  }, [loadFavorites, loadPools, loadFollowupStatuses])

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1)
  }

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

  const handleEditNotes = (record: FavoriteTalent) => {
    setEditingFavorite(record)
    setEditModalVisible(true)
  }

  const handleNotesSaved = (favoriteId: number, notes: string) => {
    setFavorites(prev => prev.map(f => (f.favorite_id === favoriteId ? { ...f, notes } : f)))
    setEditModalVisible(false)
  }

  const handleRemoveFavorite = (record: FavoriteTalent) => {
    Modal.confirm({
      title: t('user:favorites.removeTitle'),
      content: t('user:favorites.removeConfirm', { name: record.name }),
      okText: t('common:actions.confirm'),
      cancelText: t('common:actions.cancel'),
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.favorites.remove(record.talent_id)
          setFavorites(prev => prev.filter(f => f.favorite_id !== record.favorite_id))
          setTotal(prev => prev - 1)
          message.success(t('user:favorites.removed'))
        } catch {
          message.error(t('user:favorites.removeFailed'))
        }
      },
    })
  }

  const handleUpdateFollowupStatus = async (talentId: number, status: string) => {
    try {
      await api.talentPools.updateFollowupStatus(talentId, status)
      setFavorites(prev =>
        prev.map(f => (f.talent_id === talentId ? { ...f, followup_status: status } : f))
      )
      message.success(t('user:followup.updated'))
    } catch {
      message.error(t('user:followup.updateFailed'))
    }
  }

  const handlePoolCreated = () => {
    setCreatePoolModalVisible(false)
    loadPools()
  }

  const handleAddToPool = (record: FavoriteTalent) => {
    setAddingToPoolFavorite(record)
    setAddToPoolModalVisible(true)
  }

  const { exporting, exportMenu, exportConfirmVisible, confirmExport, cancelExport } =
    useExportDownload({
      getIds: () =>
        favorites.filter(f => selectedRowKeys.includes(f.favorite_id)).map(f => f.talent_id),
      emptyWarning: t('user:export.emptyWarning'),
      exportApi: (ids, format) => api.talents.export(ids, format),
      fileName: 'favorites_export',
      successMessage: count => t('user:export.success', { count }),
      formatError: () => t('user:export.failed'),
    })

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning(t('user:compare.warning'))
      return
    }
    setCompareModalVisible(true)
  }

  const columns = useFavoriteColumns({
    followupStatuses,
    onUpdateFollowupStatus: handleUpdateFollowupStatus,
    onEditNotes: handleEditNotes,
    onRemoveFavorite: handleRemoveFavorite,
    onAddToPool: handleAddToPool,
  })

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3}>
        <StarFilled style={{ marginRight: 8, color: semanticColors.gold }} />
        {t('user:favorites.title')}
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'favorites',
            label: (
              <>
                <StarFilled /> {t('user:favorites.tab')}
              </>
            ),
            children: (
              <>
                <FavoritesFilterBar
                  roleFilter={roleFilter}
                  keyword={keyword}
                  followupFilter={followupFilter}
                  followupStatuses={followupStatuses}
                  onRoleFilterChange={val => {
                    setRoleFilter(val)
                    setPage(1)
                  }}
                  onFollowupFilterChange={val => {
                    setFollowupFilter(val)
                    setPage(1)
                  }}
                  onKeywordChange={setKeyword}
                  onSearch={handleSearch}
                  onReset={handleResetFilters}
                />
                <FavoritesTableCard
                  loading={loading}
                  favorites={favorites}
                  columns={columns}
                  page={page}
                  pageSize={pageSize}
                  total={total}
                  selectedRowKeys={selectedRowKeys}
                  isAdmin={isAdmin}
                  exporting={exporting}
                  exportMenu={exportMenu}
                  onSelectionChange={setSelectedRowKeys}
                  onTableChange={handleTableChange}
                  onCompare={handleCompare}
                />
              </>
            ),
          },
          {
            key: 'pools',
            label: (
              <>
                <FolderOutlined /> {t('user:pools.tab')}
              </>
            ),
            children: (
              <TalentPoolTab
                pools={pools}
                poolsLoading={poolsLoading}
                onCreatePool={() => setCreatePoolModalVisible(true)}
              />
            ),
          },
        ]}
      />

      {/* Export Confirm Modal */}
      <ExportConfirmModal
        open={exportConfirmVisible}
        onConfirm={confirmExport}
        onCancel={cancelExport}
      />

      {/* Compare Modal */}
      <TalentCompareModal
        visible={compareModalVisible}
        talentIds={favorites
          .filter(f => selectedRowKeys.includes(f.favorite_id))
          .map(f => f.talent_id)}
        onClose={() => setCompareModalVisible(false)}
      />

      {/* Edit Notes Modal */}
      <EditNotesModal
        favorite={editingFavorite}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onSaved={handleNotesSaved}
      />

      {/* Create Pool Modal */}
      <CreatePoolModal
        open={createPoolModalVisible}
        onCancel={() => setCreatePoolModalVisible(false)}
        onCreated={handlePoolCreated}
      />

      {/* Add to Pool Modal */}
      <AddToPoolModal
        favorite={addingToPoolFavorite}
        pools={pools}
        open={addToPoolModalVisible}
        onClose={() => {
          setAddToPoolModalVisible(false)
          setAddingToPoolFavorite(null)
        }}
      />
    </div>
  )
}

export default FavoritesPage

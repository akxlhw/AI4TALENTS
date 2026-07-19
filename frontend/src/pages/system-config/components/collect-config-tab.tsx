import { Tabs } from 'antd'
import {
  SettingOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  TeamOutlined,
  CloudUploadOutlined,
  GithubOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import LabIcon from '../../../components/lab-icon'
import OSRepoConfigSubTab from './os-repo-config-sub-tab'
import OSCollectTaskSubTab from './os-collect-task-sub-tab'
import LabImportTab from './lab-import-tab'
import CompImportTab from './comp-import-tab'
import { useCollectConfig } from './collect-config-tab/useCollectConfig'
import TechDomainPanel from './collect-config-tab/tech-domain-panel'
import TaskListPanel from './collect-config-tab/task-list-panel'
import CollabSyncPanel from './collect-config-tab/collab-sync-panel'
import GenealogyPanel from './collect-config-tab/genealogy-panel'
import EmbeddingPanel from './collect-config-tab/embedding-panel'
import VenueConfigModal from './collect-config-tab/venue-config-modal'
import CollectConfirmModal from './collect-config-tab/collect-confirm-modal'
import TaskDetailModal from './collect-config-tab/task-detail-modal'

interface CollectConfigTabProps {
  initialSubTab?: string
}

const CollectConfigTab: React.FC<CollectConfigTabProps> = ({ initialSubTab }) => {
  const config = useCollectConfig(initialSubTab)

  return (
    <div>
      <Tabs
        activeKey={config.collectSubTab}
        onChange={config.setCollectSubTab}
        destroyInactiveTabPane
        items={[
          {
            key: 'tech-domains',
            label: (
              <span>
                <SettingOutlined /> 技术领域配置
              </span>
            ),
            children: (
              <TechDomainPanel
                loading={config.loading}
                techDomains={config.techDomains}
                onConfigVenues={config.handleConfigVenues}
                onOpenCollect={config.handleOpenCollect}
              />
            ),
          },
          {
            key: 'tasks',
            label: (
              <span>
                <ThunderboltOutlined /> 采集任务
              </span>
            ),
            children: (
              <TaskListPanel
                loading={config.loading}
                tasks={config.tasks}
                taskPage={config.taskPage}
                taskTotal={config.taskTotal}
                onPageChange={config.handleTaskPageChange}
                onViewTask={config.handleViewTask}
                onCancelTask={config.handleCancelTask}
                onDeleteTask={config.handleDeleteTask}
              />
            ),
          },
          {
            key: 'collaborations',
            label: (
              <span>
                <TeamOutlined /> 合作网络同步
              </span>
            ),
            children: (
              <CollabSyncPanel
                collabSyncStatus={config.collabSyncStatus}
                collabDataStatus={config.collabDataStatus}
                collabSyncLoading={config.collabSyncLoading}
                onSyncAll={config.handleSyncAllCollaborations}
                onRefresh={config.loadCollabSyncStatus}
              />
            ),
          },
          {
            key: 'genealogy',
            label: (
              <span>
                <TeamOutlined /> 学术族谱
              </span>
            ),
            children: (
              <GenealogyPanel
                genealogySyncStatus={config.genealogySyncStatus}
                genealogySyncLoading={config.genealogySyncLoading}
                onSync={config.handleSyncGenealogy}
                onRefresh={config.loadGenealogySyncStatus}
              />
            ),
          },
          {
            key: 'opensource-repos',
            label: (
              <span>
                <GithubOutlined /> 开源仓库配置
              </span>
            ),
            children: <OSRepoConfigSubTab />,
          },
          {
            key: 'opensource-tasks',
            label: (
              <span>
                <PlayCircleOutlined /> 开源采集任务
              </span>
            ),
            children: <OSCollectTaskSubTab />,
          },
          {
            key: 'lab-import',
            label: (
              <span>
                <LabIcon style={{ fontSize: 16, marginRight: 4 }} /> AI实验室人才导入
              </span>
            ),
            children: <LabImportTab />,
          },
          {
            key: 'comp-import',
            label: (
              <span>
                <TrophyOutlined style={{ marginRight: 4 }} /> 竞赛人才导入
              </span>
            ),
            children: <CompImportTab />,
          },
          {
            key: 'embeddings',
            label: (
              <span>
                <CloudUploadOutlined /> 向量生成
              </span>
            ),
            children: (
              <EmbeddingPanel
                academicProps={{
                  embeddingStatus: config.embeddingStatus,
                  embeddingProgress: config.embeddingProgress,
                  embeddingLoading: config.embeddingLoading,
                  onGenerate: config.handleGenerateEmbeddings,
                  onCancel: config.handleCancelEmbeddingGeneration,
                  onRefresh: config.loadEmbeddingStatus,
                }}
                osProps={{
                  osEmbeddingStatus: config.osEmbeddingStatus,
                  osEmbeddingProgress: config.osEmbeddingProgress,
                  osEmbeddingLoading: config.osEmbeddingLoading,
                  onGenerate: config.handleGenerateOsEmbeddings,
                  onCancel: config.handleCancelOsEmbeddingGeneration,
                  onRefresh: config.loadOsEmbeddingStatus,
                }}
              />
            ),
          },
        ]}
      />

      {/* Venue Config Modal */}
      <VenueConfigModal
        open={config.venueModalVisible}
        selectedDomain={config.selectedDomain}
        allVenues={config.allVenues}
        selectedVenueIds={config.selectedVenueIds}
        venueLoading={config.venueLoading}
        onSelectedVenueIdsChange={config.setSelectedVenueIds}
        onCancel={() => config.setVenueModalVisible(false)}
        onOk={config.handleSaveVenues}
      />

      {/* Collect Confirm Modal */}
      <CollectConfirmModal
        open={config.collectModalVisible}
        selectedDomain={config.selectedDomain}
        startYear={config.startYear}
        endYear={config.endYear}
        onStartYearChange={config.handleStartYearChange}
        onEndYearChange={config.setEndYear}
        onCancel={() => config.setCollectModalVisible(false)}
        onOk={config.handleTriggerCollect}
      />

      {/* Task Detail Modal */}
      <TaskDetailModal
        open={config.taskDetailVisible}
        task={config.selectedTask}
        onClose={() => config.setTaskDetailVisible(false)}
      />
    </div>
  )
}

export default CollectConfigTab

import {
  Modal,
  Typography,
  Button,
  Alert,
  Badge,
  Card,
  Table,
  Progress,
  Descriptions,
  Tooltip,
  Row,
  Col,
  Statistic,
} from 'antd'
import { semanticColors } from '../../../../theme'
import { useTranslation } from 'react-i18next'
import { getTaskStatusConfig } from '../../../../constants'
import '../../../../i18n/namespaces/system-config'
import type { CollectTask } from '../../../../types'
import { formatUTCToLocal } from '../../../../utils/datetime'

const { Text } = Typography

interface TaskDetailModalProps {
  open: boolean
  task: CollectTask | null
  onClose: () => void
}

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({ open, task, onClose }) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  const yearLabel = (year: number | null | undefined) =>
    year == null
      ? t('collectConfig.taskDetail.present')
      : t('collectConfig.taskDetail.year', { year })

  return (
    <Modal
      title={t('collectConfig.taskDetail.title')}
      open={open}
      onCancel={onClose}
      footer={<Button onClick={onClose}>{t('common:actions.close')}</Button>}
      width={800}
    >
      {task && (
        <>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('collectConfig.taskDetail.taskCode')}>
              {task.task_code}
            </Descriptions.Item>
            <Descriptions.Item label={t('collectConfig.taskDetail.status')}>
              <Badge
                status={getTaskStatusConfig(task.status).status}
                text={t(`collectConfig.status.${task.status}`, { defaultValue: task.status })}
              />
            </Descriptions.Item>
            <Descriptions.Item label={t('collectConfig.taskDetail.techDomain')}>
              {task.tech_domain_name}
            </Descriptions.Item>
            <Descriptions.Item label={t('collectConfig.taskDetail.timeRange')}>
              {t('collectConfig.taskDetail.timeRangeValue', {
                start: yearLabel(task.start_year),
                end: yearLabel(task.end_year),
              })}
            </Descriptions.Item>
            <Descriptions.Item label={t('collectConfig.taskDetail.currentStep')}>
              {task.current_step || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('collectConfig.taskDetail.progress')}>
              <Progress
                percent={task.progress_percent}
                status={
                  task.status === 'failed'
                    ? 'exception'
                    : task.status === 'completed'
                      ? 'success'
                      : 'active'
                }
                style={{ minWidth: 120 }}
              />
            </Descriptions.Item>
          </Descriptions>

          <Card
            title={t('collectConfig.taskDetail.statsTitle')}
            size="small"
            style={{ marginTop: 16 }}
          >
            <Row gutter={16}>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.papersCollected')}
                  value={task.total_records || 0}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.authorsFetched')}
                  value={task.result_summary?.total_authors || task.processed_records || 0}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.authorsStandardized')}
                  value={task.processed_records || 0}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.schoolsStandardized')}
                  value={task.skipped_records || 0}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.talentsSaved')}
                  value={task.success_records || 0}
                  valueStyle={{ color: semanticColors.green }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title={t('collectConfig.taskDetail.talentsUpdated')}
                  value={task.result_summary?.updated_talents || 0}
                />
              </Col>
            </Row>
            {task.result_summary && (
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={4}>
                  <Statistic
                    title={t('collectConfig.taskDetail.talentsCreated')}
                    value={task.result_summary.created_talents || 0}
                    valueStyle={{ color: semanticColors.blue }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title={t('collectConfig.taskDetail.techTags')}
                    value={task.result_summary.created_tech_tags || 0}
                  />
                </Col>
              </Row>
            )}
          </Card>

          <Card
            title={t('collectConfig.taskDetail.timeInfoTitle')}
            size="small"
            style={{ marginTop: 16 }}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label={t('collectConfig.taskDetail.triggeredAt')}>
                {formatUTCToLocal(task.triggered_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t('collectConfig.taskDetail.startedAt')}>
                {formatUTCToLocal(task.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t('collectConfig.taskDetail.completedAt')}>
                {formatUTCToLocal(task.completed_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t('collectConfig.taskDetail.duration')}>
                {task.result_summary?.total_duration || '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {task.result_summary?.venue_details && task.result_summary.venue_details.length > 0 && (
            <Card
              title={t('collectConfig.taskDetail.venueDetailsTitle')}
              size="small"
              style={{ marginTop: 16 }}
            >
              <Table
                dataSource={task.result_summary.venue_details}
                rowKey="venue_id"
                size="small"
                pagination={false}
                columns={[
                  {
                    title: t('collectConfig.taskDetail.colVenue'),
                    key: 'venue_id',
                    width: 120,
                    render: (_: unknown, record: { venue_id: number; venue_name: string }) => (
                      <Tooltip title={record.venue_name}>
                        <Text strong>{String(record.venue_id).toUpperCase()}</Text>
                      </Tooltip>
                    ),
                  },
                  {
                    title: t('collectConfig.taskDetail.colStatus'),
                    dataIndex: 'status',
                    key: 'status',
                    width: 80,
                  },
                  {
                    title: t('collectConfig.taskDetail.colFetched'),
                    dataIndex: 'fetched',
                    key: 'fetched',
                    width: 60,
                    align: 'center',
                  },
                  {
                    title: t('collectConfig.taskDetail.colSaved'),
                    dataIndex: 'saved',
                    key: 'saved',
                    width: 60,
                    align: 'center',
                  },
                  {
                    title: t('collectConfig.taskDetail.colDuration'),
                    dataIndex: 'duration',
                    key: 'duration',
                    width: 80,
                  },
                  {
                    title: t('collectConfig.taskDetail.colError'),
                    dataIndex: 'error',
                    key: 'error',
                    ellipsis: true,
                    render: (e: string) => (e ? <Text type="danger">{e}</Text> : '-'),
                  },
                ]}
              />
            </Card>
          )}

          {task.error_message && (
            <Alert
              type="error"
              message={t('collectConfig.taskDetail.errorMessage')}
              description={task.error_message}
              style={{ marginTop: 16 }}
              showIcon
            />
          )}
        </>
      )}
    </Modal>
  )
}

export default TaskDetailModal

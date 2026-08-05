import { Button, Dropdown, Space, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  DeleteOutlined,
  DownOutlined,
  EditOutlined,
  FolderOutlined,
  StarFilled,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { semanticColors } from '../../../theme'
import { getFollowupStatusConfig, getRoleTypeConfig } from '../../../constants'
import type { FavoriteTalent, FollowupStatus } from '../../../types'

const { Text } = Typography

interface UseFavoriteColumnsOptions {
  followupStatuses: FollowupStatus[]
  onUpdateFollowupStatus: (talentId: number, status: string) => void
  onEditNotes: (record: FavoriteTalent) => void
  onRemoveFavorite: (record: FavoriteTalent) => void
  onAddToPool: (record: FavoriteTalent) => void
}

export function useFavoriteColumns({
  followupStatuses,
  onUpdateFollowupStatus,
  onEditNotes,
  onRemoveFavorite,
  onAddToPool,
}: UseFavoriteColumnsOptions): ColumnsType<FavoriteTalent> {
  const navigate = useNavigate()

  return [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: FavoriteTalent) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          <Space direction="vertical" size={0}>
            <span>
              <StarFilled style={{ color: semanticColors.gold, marginRight: 6 }} />
              {name}
            </span>
            {record.name_en && (
              <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>
            )}
          </Space>
        </a>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = getRoleTypeConfig(role)
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
      render: (name: string, record: FavoriteTalent) =>
        name ? (
          <a onClick={() => record.school_id && navigate(`/schools/${record.school_id}`)}>{name}</a>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '跟进状态',
      dataIndex: 'followup_status',
      key: 'followup_status',
      width: 120,
      render: (status: string, record: FavoriteTalent) => {
        const config = getFollowupStatusConfig(status)
        return (
          <Dropdown
            trigger={['click']}
            menu={{
              items: followupStatuses.map(s => ({
                key: s.value,
                label: s.label,
              })),
              onClick: e => onUpdateFollowupStatus(record.talent_id, e.key),
            }}
          >
            <Tag color={config.color} style={{ cursor: 'pointer' }}>
              {config.text} <DownOutlined style={{ marginLeft: 4, fontSize: 10 }} />
            </Tag>
          </Dropdown>
        )
      },
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      width: 150,
      ellipsis: true,
      render: (notes: string | null) =>
        notes ? (
          <Tooltip title={notes}>
            <Text ellipsis style={{ maxWidth: 130 }}>
              {notes}
            </Text>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right' as const,
      render: (_record: FavoriteTalent, record: FavoriteTalent) => (
        <Space size="small">
          <Tooltip title="加入人才池">
            <Button
              type="text"
              size="small"
              icon={<FolderOutlined />}
              onClick={() => onAddToPool(record)}
            />
          </Tooltip>
          <Tooltip title="编辑备注">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEditNotes(record)}
            />
          </Tooltip>
          <Tooltip title="取消收藏">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onRemoveFavorite(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]
}

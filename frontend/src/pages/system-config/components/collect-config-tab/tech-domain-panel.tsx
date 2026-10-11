import { Card, Table, Typography, Tag, Space, Button, Tooltip, Empty, Spin, Badge } from 'antd'
import { SettingOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { getVenueTypeConfig } from '../../../../constants'
import '../../../../i18n/namespaces/system-config'
import type { TechDomainCollect } from '../../../../types'

const { Text } = Typography

interface TechDomainPanelProps {
  loading: boolean
  techDomains: TechDomainCollect[]
  onConfigVenues: (domain: TechDomainCollect) => void
  onOpenCollect: (domain: TechDomainCollect) => void
}

const TechDomainPanel: React.FC<TechDomainPanelProps> = ({
  loading,
  techDomains,
  onConfigVenues,
  onOpenCollect,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  const elementColumns = [
    {
      title: t('collectConfig.techDomains.colTechDomain'),
      dataIndex: 'domain_name',
      key: 'domain_name',
      width: 120,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t('collectConfig.techDomains.colVenues'),
      key: 'venues',
      render: (_: unknown, record: TechDomainCollect) => {
        const sources = record.collect_sources || []
        if (sources.length === 0)
          return <Text type="secondary">{t('collectConfig.techDomains.notConfigured')}</Text>
        const displayVenues = sources.slice(0, 10)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map(v => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {sources.length > 10 && <Tag>+{sources.length - 10}</Tag>}
          </Space>
        )
      },
    },
    {
      title: t('collectConfig.techDomains.colVenueCount'),
      dataIndex: 'venue_count',
      key: 'venue_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color="blue" style={{ marginRight: 8 }} />
      ),
    },
    {
      title: t('collectConfig.techDomains.colActions'),
      key: 'actions',
      width: 180,
      render: (_: unknown, record: TechDomainCollect) => (
        <Space>
          <Tooltip title={t('collectConfig.techDomains.configVenuesTooltip')}>
            <Button
              type="link"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => onConfigVenues(record)}
            >
              {t('collectConfig.techDomains.configAction')}
            </Button>
          </Tooltip>
          <Tooltip title={t('collectConfig.techDomains.collectTooltip')}>
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => onOpenCollect(record)}
              disabled={!record.collect_sources || record.collect_sources.length === 0}
            >
              {t('collectConfig.techDomains.collectAction')}
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <Spin spinning={loading}>
        <Table
          dataSource={techDomains}
          columns={elementColumns}
          rowKey="tech_domain_id"
          pagination={false}
          locale={{
            emptyText: <Empty description={t('collectConfig.techDomains.empty')} />,
          }}
        />
      </Spin>
    </Card>
  )
}

export default TechDomainPanel

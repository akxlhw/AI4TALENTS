import { Alert, Collapse, Drawer, Empty, Space, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

import { CHANGELOG_RELEASES, type ChangelogRelease } from '../utils/changelog'

const { Text, Title } = Typography

const GROUP_COLORS: Record<string, string> = {
  Added: 'green',
  Changed: 'blue',
  Fixed: 'orange',
  Removed: 'red',
  Security: 'purple',
}

/** 更新日志抽屉：按版本时间线展示 CHANGELOG.md（构建期打包），
 * 最新一版默认展开，其余折叠；解析失败降级为空态。 */
const ChangelogDrawer: React.FC<{
  open: boolean
  onClose: () => void
  /** 仅供测试：强制渲染空态 */
  forceEmpty?: boolean
}> = ({ open, onClose, forceEmpty = false }) => {
  const { t } = useTranslation('common')
  const list: ChangelogRelease[] = forceEmpty ? [] : CHANGELOG_RELEASES
  const latestVersion = CHANGELOG_RELEASES[0]?.version

  return (
    <Drawer
      title={
        <Space direction="vertical" size={0}>
          <Title level={5} style={{ margin: 0 }}>
            {t('changelog.title')}
          </Title>
          {latestVersion && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('changelog.currentVersion', { version: latestVersion })}
            </Text>
          )}
        </Space>
      }
      placement="right"
      width={520}
      open={open}
      onClose={onClose}
    >
      {list.length === 0 ? (
        <Empty description={t('changelog.empty')} style={{ marginTop: 80 }} />
      ) : (
        <>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={t('changelog.orderingHint')}
          />
          <Collapse
            defaultActiveKey={[list[0].version]}
            items={list.map(r => ({
              key: r.version,
              label: (
                <Space size={8}>
                  <Text strong>v{r.version}</Text>
                  {r === list[0] && (
                    <Tag color="geekblue" style={{ margin: 0 }}>
                      {t('changelog.latest')}
                    </Tag>
                  )}
                  {r.date && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {r.date}
                    </Text>
                  )}
                </Space>
              ),
              children: (
                <div>
                  {r.intro && (
                    <Text
                      type="secondary"
                      style={{ display: 'block', marginBottom: 8, fontSize: 12 }}
                    >
                      {r.intro}
                    </Text>
                  )}
                  {r.sections.map(section => (
                    <div key={section.group} style={{ marginBottom: 12 }}>
                      <Tag
                        color={GROUP_COLORS[section.group] ?? 'default'}
                        style={{ marginBottom: 4 }}
                      >
                        {section.group}
                      </Tag>
                      {section.items.map((item, i) => (
                        <Text
                          key={i}
                          style={{
                            display: 'block',
                            fontSize: 13,
                            lineHeight: '22px',
                            paddingLeft: item.level === 2 ? 20 : 0,
                            color:
                              item.level === 2 ? 'var(--text-secondary)' : undefined,
                          }}
                        >
                          {item.text}
                        </Text>
                      ))}
                    </div>
                  ))}
                </div>
              ),
            }))}
          />
        </>
      )}
    </Drawer>
  )
}

export default ChangelogDrawer

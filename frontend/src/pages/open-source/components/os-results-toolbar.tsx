import { Button, Checkbox, Dropdown, Space, Typography, type MenuProps } from 'antd'
import { DownOutlined, DownloadOutlined } from '@ant-design/icons'
import { Trans, useTranslation } from 'react-i18next'
import '@/i18n/namespaces/open-source'

const { Text } = Typography

interface OsResultsToolbarProps {
  total: number
  showControls: boolean
  isPageAllSelected: boolean
  selectedCount: number
  isAdmin: boolean
  exporting: boolean
  exportMenu: MenuProps
  onSelectPage: () => void
  onSelectAll: () => void
  onClearSelection: () => void
}

const OsResultsToolbar: React.FC<OsResultsToolbarProps> = ({
  total,
  showControls,
  isPageAllSelected,
  selectedCount,
  isAdmin,
  exporting,
  exportMenu,
  onSelectPage,
  onSelectAll,
  onClearSelection,
}) => {
  const { t } = useTranslation(['openSource', 'common'])

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 16,
      }}
    >
      <Text style={{ color: 'var(--text-secondary)' }}>
        {t('openSource:search.resultCount', { n: total })}
      </Text>
      {showControls && (
        <Space wrap>
          <Checkbox checked={isPageAllSelected} onChange={onSelectPage}>
            {t('openSource:results.selectPage')}
          </Checkbox>
          <Button size="small" onClick={onSelectAll}>
            {t('openSource:results.selectAll')}
          </Button>
          <Text>
            <Trans
              ns="openSource"
              i18nKey="results.selectedCount"
              values={{ n: selectedCount }}
              components={{ strong: <strong /> }}
            />
          </Text>
          {selectedCount > 0 && (
            <Button size="small" onClick={onClearSelection}>
              {t('openSource:results.cancelSelection')}
            </Button>
          )}
          {isAdmin && (
            <Dropdown menu={exportMenu} trigger={['click']}>
              <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                {t('common:actions.export')} <DownOutlined />
              </Button>
            </Dropdown>
          )}
        </Space>
      )}
    </div>
  )
}

export default OsResultsToolbar

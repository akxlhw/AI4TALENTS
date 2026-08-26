import React, { useMemo, useState } from 'react'
import { Tabs, Typography } from 'antd'
import { ApiOutlined, KeyOutlined, ThunderboltOutlined, GlobalOutlined, GithubOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import CollectConfigTab from './components/collect-config-tab'
import LLMConfigTab from './components/llm-config-tab'
import ProxyConfigTab from './components/proxy-config-tab'
import GitHubConfigTab from './components/github-config-tab'
import ApiKeysTab from './api-keys-tab'

const { Title } = Typography

type TabKey = 'collect' | 'llm' | 'proxy' | 'github' | 'api-keys'

const MAIN_TAB_KEYS: TabKey[] = ['collect', 'llm', 'proxy', 'github', 'api-keys']

const COLLECT_SUB_TAB_KEYS = [
  'tech-domains',
  'tasks',
  'collaborations',
  'genealogy',
  'opensource-repos',
  'opensource-tasks',
  'lab-import',
  'comp-import',
  'industry-positions',
  'industry-import',
  'embeddings',
]

const SystemConfigPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()

  const { initialActiveTab, initialCollectSubTab } = useMemo(() => {
    const tabParam = searchParams.get('tab') || ''
    if ((MAIN_TAB_KEYS as string[]).includes(tabParam)) {
      return { initialActiveTab: tabParam as TabKey, initialCollectSubTab: undefined }
    }
    if (COLLECT_SUB_TAB_KEYS.includes(tabParam)) {
      return { initialActiveTab: 'collect' as TabKey, initialCollectSubTab: tabParam }
    }
    return { initialActiveTab: 'collect' as TabKey, initialCollectSubTab: undefined }
  }, [searchParams])

  const [activeTab, setActiveTab] = useState<TabKey>(initialActiveTab)

  const handleTabChange = (key: string) => {
    const next = key as TabKey
    setActiveTab(next)
    setSearchParams({ tab: next })
  }

  const tabItems = [
    {
      key: 'collect' as TabKey,
      label: (
        <span>
          <ThunderboltOutlined style={{ marginRight: 6 }} />
          采集配置
        </span>
      ),
      children: <CollectConfigTab initialSubTab={initialCollectSubTab} />,
    },
    {
      key: 'llm' as TabKey,
      label: (
        <span>
          <ApiOutlined style={{ marginRight: 6 }} />
          LLM 配置
        </span>
      ),
      children: <LLMConfigTab />,
    },
    {
      key: 'proxy' as TabKey,
      label: (
        <span>
          <GlobalOutlined style={{ marginRight: 6 }} />
          代理配置
        </span>
      ),
      children: <ProxyConfigTab />,
    },
    {
      key: 'github' as TabKey,
      label: (
        <span>
          <GithubOutlined style={{ marginRight: 6 }} />
          GitHub 配置
        </span>
      ),
      children: <GitHubConfigTab />,
    },
    {
      key: 'api-keys' as TabKey,
      label: (
        <span>
          <KeyOutlined style={{ marginRight: 6 }} />
          API Key 管理
        </span>
      ),
      children: <ApiKeysTab />,
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={4}>系统配置</Title>
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        items={tabItems}
        destroyInactiveTabPane={false}
      />
    </div>
  )
}

export default SystemConfigPage

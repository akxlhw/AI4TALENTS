import React, { useState } from 'react'
import { Tabs, Typography } from 'antd'
import {
  ApiOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  GithubOutlined,
} from '@ant-design/icons'
import CollectConfigTab from './CollectConfigTab'
import LLMConfigTab from './LLMConfigTab'
import ProxyConfigTab from './ProxyConfigTab'
import GitHubConfigTab from './GitHubConfigTab'

const { Title } = Typography

type TabKey = 'collect' | 'llm' | 'proxy' | 'github'

const SystemConfigPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('collect')

  const tabItems = [
    {
      key: 'collect' as TabKey,
      label: (
        <span>
          <ThunderboltOutlined style={{ marginRight: 6 }} />
          采集配置
        </span>
      ),
      children: <CollectConfigTab />,
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
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={4}>系统配置</Title>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as TabKey)}
        items={tabItems}
        destroyInactiveTabPane={false}
      />
    </div>
  )
}

export default SystemConfigPage

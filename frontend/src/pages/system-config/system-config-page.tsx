import React, { useState } from 'react'
import { Tabs, Typography } from 'antd'
import {
  ApiOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  GithubOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import CollectConfigTab from './components/collect-config-tab'
import LLMConfigTab from './components/llm-config-tab'
import ProxyConfigTab from './components/proxy-config-tab'
import GitHubConfigTab from './components/github-config-tab'
import LabImportTab from './components/lab-import-tab'

const { Title } = Typography

type TabKey = 'collect' | 'llm' | 'proxy' | 'github' | 'lab'

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
    {
      key: 'lab' as TabKey,
      label: (
        <span>
          <ExperimentOutlined style={{ marginRight: 6 }} />
          实验室人才导入
        </span>
      ),
      children: <LabImportTab />,
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

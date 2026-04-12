import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Dropdown, Avatar, Space, Typography, Tag } from 'antd'
import {
  HomeOutlined,
  SearchOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  StarOutlined,
  AppstoreOutlined,
  GlobalOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const { Header, Content, Sider } = Layout
const { Text } = Typography

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin } = useAuth()

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/tech-element',
      icon: <AppstoreOutlined />,
      label: '技术要素',
    },
    {
      key: '/country-school',
      icon: <GlobalOutlined />,
      label: '院校机构',
    },
    {
      key: '/search',
      icon: <SearchOutlined />,
      label: '人才搜索',
    },
    {
      key: '/jd-match',
      icon: <RobotOutlined />,
      label: 'JD 匹配',
    },
    {
      key: '/recommend',
      icon: <TeamOutlined />,
      label: '智能推荐',
    },
    {
      key: '/favorites',
      icon: <StarOutlined />,
      label: '我的收藏',
    },
    ...(isAdmin ? [{
      key: '/admin',
      icon: <SettingOutlined />,
      label: '权限管理',
    }] : []),
    ...(isAdmin ? [{
      key: '/collect',
      icon: <ThunderboltOutlined />,
      label: '采集配置',
    }] : []),
    ...(isAdmin ? [{
      key: '/data-version',
      icon: <DatabaseOutlined />,
      label: '数据版本',
    }] : []),
  ]

  const handleMenuClick = (key: string) => {
    navigate(key)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      handleLogout()
    } else if (key === 'profile') {
      navigate('/profile')
    }
  }

  const roleColorMap: Record<string, string> = {
    super_admin: 'red',
    admin: 'orange',
    user: 'blue',
  }

  const roleTextMap: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '管理员',
    user: '普通用户',
  }

  // 高亮当前选中的菜单项
  const selectedKey = location.pathname === '/' ? '/' : '/' + location.pathname.split('/')[1]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#001529',
          padding: '0 24px',
        }}
      >
        <div
          style={{
            color: 'white',
            fontSize: '18px',
            fontWeight: 'bold',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/')}
        >
          智能学术界人才库
        </div>

        {user && (
          <Dropdown
            menu={{
              items: userMenuItems,
              onClick: handleUserMenuClick,
            }}
            placement="bottomRight"
          >
            <Space style={{ cursor: 'pointer', color: 'white' }}>
              <Avatar
                style={{ backgroundColor: '#1890ff' }}
                icon={<UserOutlined />}
              />
              <Text style={{ color: 'white' }}>
                {user.display_name || user.username}
              </Text>
              <Tag color={roleColorMap[user.role] || 'default'} style={{ margin: 0 }}>
                {roleTextMap[user.role] || user.role}
              </Tag>
            </Space>
          </Dropdown>
        )}
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
            onClick={({ key }) => handleMenuClick(key)}
          />
        </Sider>
        <Layout style={{ padding: '0 24px 24px' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: '#fff',
              borderRadius: 8,
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default MainLayout

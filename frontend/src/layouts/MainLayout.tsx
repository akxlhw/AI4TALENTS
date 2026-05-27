import { useState, useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { Dropdown, Avatar, Space, Typography, Tag, Tooltip, Button } from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  DatabaseOutlined,
  StarOutlined,
  BookOutlined,
  CodeOutlined,
  TrophyOutlined,
  BuildOutlined,
  LockOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { useDomainStore } from '../stores/domainStore'
import { domainThemes, semanticColors, type Domain } from '../theme'
import Footer from '../components/Footer'

const { Text } = Typography

interface DomainNavItem {
  key: Domain
  icon: React.ReactNode
  soon?: boolean
}

const domainNavItems: DomainNavItem[] = [
  { key: 'academic', icon: <BookOutlined /> },
  { key: 'opensource', icon: <CodeOutlined /> },
  { key: 'competition', icon: <TrophyOutlined />, soon: true },
  { key: 'industry', icon: <BuildOutlined />, soon: true },
]

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const { user, logout, isAdmin } = useAuth()
  const { currentDomain, setDomain, isDomainAvailable } = useDomainStore()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
    ...(isAdmin ? [
      { type: 'divider' as const },
      { key: 'admin', icon: <SettingOutlined />, label: '用户管理' },
      { key: 'system-config', icon: <SettingOutlined />, label: '系统配置' },
      { key: 'data-version', icon: <DatabaseOutlined />, label: '数据管理' },
      { key: 'audit-logs', icon: <DatabaseOutlined />, label: '审计日志' },
      { key: 'suggestion-admin', icon: <MessageOutlined />, label: '建议管理' },
    ] : []),
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ]

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') handleLogout()
    else if (key === 'profile') navigate('/profile')
    else if (key === 'admin') navigate('/admin')
    else if (key === 'system-config') navigate('/system-config')
    else if (key === 'data-version') navigate('/data-version')
    else if (key === 'audit-logs') navigate('/audit-logs')
    else if (key === 'suggestion-admin') navigate('/suggestion-admin')
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

  const handleDomainSwitch = (domain: Domain) => {
    if (isDomainAvailable(domain)) {
      setDomain(domain)
      navigate('/')
    } else {
      navigate(`/demo-${domain}`)
    }
  }

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      {/* ========== Top Nav — Transparent → Frosted on scroll ========== */}
      <nav
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          transition: 'all 0.3s ease',
          background: scrolled ? 'rgba(255,255,255,0.92)' : 'transparent',
          backdropFilter: scrolled ? 'blur(12px)' : 'none',
          borderBottom: scrolled ? '1px solid var(--border-secondary)' : '1px solid transparent',
          boxShadow: scrolled ? 'var(--shadow-sm)' : 'none',
        }}
      >
        {/* Left: Logo + Domain Switcher */}
        <Space size={16} style={{ flex: 1, overflow: 'hidden' }}>
          {/* Logo */}
          <Space
            style={{ cursor: 'pointer', flexShrink: 0 }}
            onClick={() => navigate('/')}
          >
            <Text
              style={{
                fontSize: 18,
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '-0.5px',
              }}
            >
              AI4TALENT
            </Text>
            <Text
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                letterSpacing: '0.5px',
              }}
            >
              智能人才库
            </Text>
          </Space>

          {/* Divider */}
          <div
            style={{
              width: 1.5,
              height: 20,
              background: semanticColors.divider,
              borderRadius: 1,
              flexShrink: 0,
            }}
          />

          {/* Domain Switcher */}
          <Space size={2} style={{ flexShrink: 0 }}>
            {domainNavItems.map((d) => {
              const theme = domainThemes[d.key]
              const isActive = currentDomain === d.key
              return (
                <Tooltip
                  key={d.key}
                  title={d.soon ? `${theme.label}（即将上线）` : theme.label}
                  placement="bottom"
                >
                  <button
                    onClick={() => handleDomainSwitch(d.key)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                      padding: '5px 12px',
                      borderRadius: 6,
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 13,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? '#fff' : 'var(--text-secondary)',
                      background: isActive
                        ? theme.primary
                        : 'transparent',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'var(--bg-layout)'
                        e.currentTarget.style.color = 'var(--text-primary)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent'
                        e.currentTarget.style.color = 'var(--text-secondary)'
                      }
                    }}
                  >
                    <span style={{ fontSize: 14, display: 'flex', alignItems: 'center' }}>
                      {d.icon}
                    </span>
                    <span>{theme.shortLabel}</span>
                    {d.soon && (
                      <LockOutlined style={{ fontSize: 10, opacity: isActive ? 0.7 : 0.35 }} />
                    )}
                  </button>
                </Tooltip>
              )
            })}
          </Space>


        </Space>

        {/* Right: User actions */}
        {user && (
          <Space size={8} style={{ flexShrink: 0 }}>
            <Button
              type="text"
              size="small"
              icon={<StarOutlined />}
              onClick={() => navigate('/favorites')}
              style={{ fontSize: 13 }}
            >
              我的收藏
            </Button>
            <Button
              type="text"
              size="small"
              icon={<MessageOutlined />}
              onClick={() => navigate('/feedback')}
              style={{ fontSize: 13 }}
            >
              意见反馈
            </Button>
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }} size={8}>
                <Avatar
                  style={{ background: 'var(--domain-gradient)', fontSize: 12 }}
                  icon={<UserOutlined />}
                  size="small"
                />
                <Text style={{ color: 'var(--text-primary)', fontSize: 13 }}>
                  {user.display_name || user.username}
                </Text>
                <Tag
                  color={roleColorMap[user.role] || 'default'}
                  style={{ margin: 0, fontSize: 10, padding: '0 5px', lineHeight: '16px' }}
                >
                  {roleTextMap[user.role] || user.role}
                </Tag>
              </Space>
            </Dropdown>
          </Space>
        )}
      </nav>

      {/* ========== Content Area ========== */}
      <main className="discovery-content" style={{ paddingTop: 0, minHeight: 'calc(100vh - 64px)' }}>
        <Outlet />
      </main>

      <Footer />
    </div>
  )
}

export default MainLayout

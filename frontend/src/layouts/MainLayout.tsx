import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Dropdown, Avatar, Space, Typography, Tag, Tooltip, Button } from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  DatabaseOutlined,
  HomeOutlined,
  BookOutlined,
  StarOutlined,
  CodeOutlined,
  TrophyOutlined,
  BuildOutlined,
  LockOutlined,

  DownOutlined,
  UpOutlined,
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { useDomainStore } from '../stores/domainStore'
import { domainThemes, type Domain } from '../theme'

const { Text } = Typography

interface DomainNavItem {
  key: Domain
  icon: React.ReactNode
  soon?: boolean
}

const domainNavItems: DomainNavItem[] = [
  { key: 'academic', icon: <BookOutlined /> },
  { key: 'opensource', icon: <CodeOutlined />, soon: true },
  { key: 'competition', icon: <TrophyOutlined />, soon: true },
  { key: 'industry', icon: <BuildOutlined />, soon: true },
]

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isAdmin } = useAuth()
  const isHome = location.pathname === '/'
  const { currentDomain, setDomain, isDomainAvailable } = useDomainStore()
  const [scrolled, setScrolled] = useState(false)
  const [dockOpen, setDockOpen] = useState(false)

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
    <div style={{ minHeight: '100vh', position: 'relative', paddingBottom: 80 }}>
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
        {/* Logo + Home */}
        <Space size={16}>
          <Space
            style={{ cursor: 'pointer' }}
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
                fontSize: 15,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                letterSpacing: '1px',
              }}
            >
              智能人才库
            </Text>
          </Space>

          {!isHome && (
            <Button
              type="text"
              size="small"
              icon={<HomeOutlined />}
              onClick={() => navigate('/')}
              style={{ fontSize: 13 }}
            >
              首页
            </Button>
          )}
        </Space>

        {/* Nav actions — pushed to right */}
        {user && (
          <Space size={8}>
            <Button
              type="text"
              size="small"
              icon={<StarOutlined />}
              onClick={() => navigate('/favorites')}
              style={{ fontSize: 13 }}
            >
              我的收藏
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

      {/* ========== Content Area — Full Width, No Sidebar ========== */}
      <main className="discovery-content" style={{ paddingTop: 0 }}>
        <Outlet />
      </main>

      {/* ========== Collapsible Bottom Dock ========== */}
      <div className="dock-container" style={{ position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 100 }}>
        {dockOpen ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 12px',
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(12px)',
              borderRadius: 20,
              border: '1px solid var(--border-secondary)',
              boxShadow: 'var(--shadow-lg)',
              animation: 'dock-pop 0.2s ease-out',
            }}
          >
            <button
              onClick={() => setDockOpen(false)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 32,
                height: 32,
                borderRadius: 12,
                border: 'none',
                cursor: 'pointer',
                background: 'var(--bg-layout)',
                color: 'var(--text-secondary)',
              }}
            >
              <UpOutlined style={{ fontSize: 12 }} />
            </button>
            {domainNavItems.map((d) => {
              const theme = domainThemes[d.key]
              const isActive = currentDomain === d.key
              return (
                <Tooltip
                  key={d.key}
                  title={d.soon ? `${theme.label}（即将上线）` : theme.label}
                  placement="top"
                >
                  <button
                    onClick={() => handleDomainSwitch(d.key)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: isActive ? '8px 16px' : '8px 12px',
                      borderRadius: 16,
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 13,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? '#fff' : 'var(--text-secondary)',
                      background: isActive ? theme.primary : 'transparent',
                      boxShadow: isActive ? `0 4px 12px ${theme.primary}44` : 'none',
                      transition: 'all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)',
                    }}
                  >
                    <span style={{ fontSize: 16 }}>{d.icon}</span>
                    {isActive && <span>{theme.shortLabel}</span>}
                    {d.soon && !isActive && (
                      <LockOutlined style={{ fontSize: 10, opacity: 0.4 }} />
                    )}
                  </button>
                </Tooltip>
              )
            })}
          </div>
        ) : (
          <button
            onClick={(e) => {
              e.stopPropagation()
              setDockOpen(true)
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '10px 18px',
              borderRadius: 20,
              border: 'none',
              cursor: 'pointer',
              fontSize: 13,
              color: '#fff',
              background: domainThemes[currentDomain].primary,
              boxShadow: `0 4px 14px ${domainThemes[currentDomain].primary}55`,
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)' }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)' }}
          >
            <span style={{ fontSize: 16 }}>{domainNavItems.find((d) => d.key === currentDomain)?.icon}</span>
            <span>{domainThemes[currentDomain].shortLabel}</span>
            <DownOutlined style={{ fontSize: 11, opacity: 0.7 }} />
          </button>
        )}
      </div>
    </div>
  )
}

export default MainLayout

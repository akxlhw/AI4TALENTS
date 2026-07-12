import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Typography, Input } from 'antd'
import { SearchOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography
const { Search } = Input

const LabHero: React.FC = () => {
  const navigate = useNavigate()
  const [searchValue, setSearchValue] = useState('')

  const handleSearch = (value: string) => {
    if (value.trim()) {
      navigate(`/lab/search?keyword=${encodeURIComponent(value.trim())}`)
    }
  }

  return (
    <div
      style={{
        background: 'var(--domain-gradient)',
        padding: '64px 32px 48px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.06,
          backgroundImage:
            'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }}
      />
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 880, margin: '0 auto' }}>
        <Title
          level={1}
          style={{
            margin: 0,
            marginBottom: 16,
            color: '#fff',
            fontWeight: 800,
            fontSize: 46,
            letterSpacing: '-0.5px',
          }}
        >
          AI Native人才库
        </Title>
        <Paragraph
          style={{
            margin: 0,
            marginBottom: 40,
            color: 'rgba(255,255,255,0.85)',
            fontSize: 16,
          }}
        >
          基于全球 AI 实验室公开信息的人才发现平台 · 汇聚连接顶尖 AI 原生人才
        </Paragraph>

        <Search
          placeholder="输入姓名、实验室、研究方向等关键词搜索人才..."
          enterButton={
            <span style={{ fontWeight: 500 }}>
              <SearchOutlined /> 搜索
            </span>
          }
          size="large"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onSearch={handleSearch}
          style={{ width: '100%', margin: '0 auto' }}
        />
      </div>
    </div>
  )
}

export default LabHero

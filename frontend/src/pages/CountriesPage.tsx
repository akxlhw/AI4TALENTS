import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Table, Typography, Spin, Badge, Input, Space } from 'antd'
import { GlobalOutlined, SearchOutlined } from '@ant-design/icons'
import { api } from '../services/api'

const { Title } = Typography

interface Country {
  country_id: number
  country_code: string
  country_name_cn: string
  country_name_en: string | null
  school_count: number
  professor_count: number
}

interface School {
  school_id: number
  school_name: string
  school_alias: string | null
  country_name: string | null
  professor_count: number
  student_count: number
  homepage_url: string | null
}

const CountriesPage: React.FC = () => {
  const navigate = useNavigate()
  const [countries, setCountries] = useState<Country[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null)
  const [loading, setLoading] = useState(false)
  const [schoolsLoading, setSchoolsLoading] = useState(false)
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    fetchCountries()
  }, [])

  const fetchCountries = async () => {
    setLoading(true)
    try {
      const response = await api.countries.list()
      setCountries(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch countries:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSchools = async (countryId: number) => {
    setSchoolsLoading(true)
    try {
      const response = await api.schools.list({ country_id: countryId })
      setSchools(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch schools:', error)
    } finally {
      setSchoolsLoading(false)
    }
  }

  const handleCountryClick = (country: Country) => {
    setSelectedCountry(country)
    fetchSchools(country.country_id)
  }

  const filteredCountries = countries.filter(c =>
    !searchText ||
    c.country_name_cn.includes(searchText) ||
    c.country_name_en?.toLowerCase().includes(searchText.toLowerCase()) ||
    c.country_code.toLowerCase().includes(searchText.toLowerCase())
  )

  const countryColumns = [
    {
      title: '国家',
      dataIndex: 'country_name_cn',
      key: 'country_name_cn',
      render: (text: string, record: Country) => (
        <a onClick={() => handleCountryClick(record)}>
          <Space>
            <GlobalOutlined />
            {text}
            {record.country_name_en && (
              <span style={{ color: '#999', fontSize: 12 }}>
                ({record.country_name_en})
              </span>
            )}
          </Space>
        </a>
      ),
    },
    {
      title: '代码',
      dataIndex: 'country_code',
      key: 'country_code',
      width: 80,
    },
    {
      title: '学校数',
      dataIndex: 'school_count',
      key: 'school_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#1890ff' }} />
      ),
    },
    {
      title: '教授数',
      dataIndex: 'professor_count',
      key: 'professor_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      ),
    },
  ]

  const schoolColumns = [
    {
      title: '学校名称',
      dataIndex: 'school_name',
      key: 'school_name',
      render: (text: string, record: School) => (
        <a onClick={() => navigate(`/schools/${record.school_id}`)}>
          {text}
        </a>
      ),
    },
    {
      title: '别名',
      dataIndex: 'school_alias',
      key: 'school_alias',
      ellipsis: true,
    },
    {
      title: '教授',
      dataIndex: 'professor_count',
      key: 'professor_count',
      width: 80,
    },
    {
      title: '学生',
      dataIndex: 'student_count',
      key: 'student_count',
      width: 80,
    },
    {
      title: '主页',
      dataIndex: 'homepage_url',
      key: 'homepage_url',
      width: 100,
      render: (url: string | null) =>
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            访问
          </a>
        ) : null,
    },
  ]

  return (
    <div>
      <Title level={3}>
        <GlobalOutlined style={{ marginRight: 8 }} />
        国家/学校浏览
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索国家..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
      </Card>

      <div style={{ display: 'flex', gap: 16 }}>
        <Card
          title="国家列表"
          style={{ flex: '0 0 400px' }}
          bodyStyle={{ padding: 0 }}
        >
          <Spin spinning={loading}>
            <Table
              dataSource={filteredCountries}
              columns={countryColumns}
              rowKey="country_id"
              pagination={false}
              size="small"
              onRow={(record) => ({
                onClick: () => handleCountryClick(record),
                style: { cursor: 'pointer' },
              })}
              rowClassName={(record) =>
                selectedCountry?.country_id === record.country_id
                  ? 'ant-table-row-selected'
                  : ''
              }
            />
          </Spin>
        </Card>

        <Card
          title={selectedCountry ? `${selectedCountry.country_name_cn}的学校` : '请选择国家'}
          style={{ flex: 1 }}
          bodyStyle={{ padding: 0 }}
        >
          <Spin spinning={schoolsLoading}>
            <Table
              dataSource={schools}
              columns={schoolColumns}
              rowKey="school_id"
              pagination={{ pageSize: 10 }}
              size="small"
              locale={{ emptyText: selectedCountry ? '暂无学校数据' : '请先选择一个国家' }}
            />
          </Spin>
        </Card>
      </div>
    </div>
  )
}

export default CountriesPage

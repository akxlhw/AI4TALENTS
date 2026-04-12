/**
 * JD Match Page - v1.4
 *
 * 功能说明：
 * - 输入职位描述(JD)，使用 LLM 解析关键特征
 * - 智能匹配合适的人才
 * - 显示匹配分数和匹配原因
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Typography,
  Input,
  Button,
  Space,
  Table,
  Tag,
  Progress,
  Empty,
  Spin,
  Alert,
  message,
  Descriptions,
  List,
} from 'antd'
import {
  RobotOutlined,
  SearchOutlined,
  BulbOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import type { JDFeatures, MatchResultItem } from '../types'

const { Title, Text } = Typography
const { TextArea } = Input

const JDMatchPage: React.FC = () => {
  const navigate = useNavigate()

  // State
  const [jdText, setJdText] = useState('')
  const [loading, setLoading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [jdFeatures, setJdFeatures] = useState<JDFeatures | null>(null)
  const [matchResults, setMatchResults] = useState<MatchResultItem[]>([])
  const [tookMs, setTookMs] = useState<number | null>(null)

  // Parse JD text
  const handleParseJD = async () => {
    if (!jdText.trim()) {
      message.warning('请输入职位描述')
      return
    }

    setParsing(true)
    try {
      const response = await api.jdMatch.parse(jdText)
      setJdFeatures(response.data)
      message.success('JD 解析成功')
    } catch (error: unknown) {
      console.error('Parse JD failed:', error)
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || 'JD 解析失败')
    } finally {
      setParsing(false)
    }
  }

  // Match talents
  const handleMatch = async () => {
    if (!jdText.trim()) {
      message.warning('请输入职位描述')
      return
    }

    setLoading(true)
    try {
      const response = await api.jdMatch.match({
        jd_text: jdText,
        config: {
          weights: { skill: 0.4, research: 0.3, experience: 0.2, education: 0.1 },
          limit: 20,
        },
      })
      setMatchResults(response.data.items || [])
      setTookMs(response.data.took_ms)

      // Also parse JD if not already done
      if (!jdFeatures) {
        const parseResponse = await api.jdMatch.parse(jdText)
        setJdFeatures(parseResponse.data)
      }

      message.success(`找到 ${response.data.total} 位匹配候选人`)
    } catch (error: unknown) {
      console.error('Match failed:', error)
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '匹配失败，请检查 LLM 配置')
    } finally {
      setLoading(false)
    }
  }

  // Reset
  const handleReset = () => {
    setJdText('')
    setJdFeatures(null)
    setMatchResults([])
    setTookMs(null)
  }

  // Table columns
  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: MatchResultItem, index: number) => (
        <Tag color={index < 3 ? 'gold' : 'default'}>
          {index + 1}
        </Tag>
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: MatchResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          {name}
        </a>
      ),
    },
    {
      title: '职位',
      dataIndex: 'title',
      key: 'title',
      width: 150,
      ellipsis: true,
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '综合分数',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 150,
      render: (score: number) => (
        <Progress
          percent={score}
          size="small"
          status={score >= 70 ? 'success' : score >= 50 ? 'normal' : 'exception'}
          format={(percent) => `${percent?.toFixed(0)}分`}
        />
      ),
      sorter: (a: MatchResultItem, b: MatchResultItem) => a.overall_score - b.overall_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '技能匹配',
      dataIndex: 'skill_score',
      key: 'skill_score',
      width: 100,
      render: (score: number) => (
        <Tag color={score >= 70 ? 'green' : score >= 40 ? 'blue' : 'default'}>
          {score.toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: '研究方向',
      dataIndex: 'research_score',
      key: 'research_score',
      width: 100,
      render: (score: number) => (
        <Tag color={score >= 70 ? 'green' : score >= 40 ? 'blue' : 'default'}>
          {score.toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: '匹配技能',
      dataIndex: 'highlight_skills',
      key: 'highlight_skills',
      width: 200,
      render: (skills: string[]) => (
        <Space size={[4, 4]} wrap>
          {skills?.slice(0, 5).map((skill, idx) => (
            <Tag key={idx} color="blue" style={{ margin: 0 }}>
              {skill}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '匹配原因',
      dataIndex: 'match_reasons',
      key: 'match_reasons',
      width: 250,
      render: (reasons: string[]) => (
        <List
          size="small"
          dataSource={reasons?.slice(0, 3) || []}
          renderItem={(item) => (
            <List.Item style={{ padding: '2px 0', border: 'none' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                • {item}
              </Text>
            </List.Item>
          )}
        />
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>
        <RobotOutlined style={{ marginRight: 8 }} />
        JD 智能匹配
        {tookMs && (
          <Text type="secondary" style={{ fontSize: 14, marginLeft: 12, fontWeight: 'normal' }}>
            耗时 {tookMs.toFixed(0)}ms
          </Text>
        )}
      </Title>

      <Alert
        message="功能说明"
        description="输入职位描述(JD)，系统将使用 LLM 解析关键特征（技能、经验、研究方向等），并智能匹配合适的人才。需要配置 LLM API Key。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* JD Input */}
      <Card title="职位描述 (JD)" style={{ marginBottom: 16 }}>
        <TextArea
          placeholder="请粘贴职位描述内容，包括岗位职责、任职要求、技能要求等..."
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={6}
          showCount
          maxLength={5000}
        />
        <Space style={{ marginTop: 12 }}>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleMatch}
            loading={loading}
          >
            智能匹配
          </Button>
          <Button
            icon={<BulbOutlined />}
            onClick={handleParseJD}
            loading={parsing}
          >
            解析 JD
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
          >
            重置
          </Button>
        </Space>
      </Card>

      {/* JD Features */}
      {jdFeatures && (
        <Card title="JD 解析结果" style={{ marginBottom: 16 }} size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="技能要求">
              <Space size={[4, 4]} wrap>
                {jdFeatures.skills?.map((skill, idx) => (
                  <Tag key={idx} color="blue">{skill}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="经验要求">
              {jdFeatures.experience || '未指定'}
            </Descriptions.Item>
            <Descriptions.Item label="研究方向">
              <Space size={[4, 4]} wrap>
                {jdFeatures.research_areas?.map((area, idx) => (
                  <Tag key={idx} color="green">{area}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="角色类型">
              <Tag color="purple">{jdFeatures.role_type || '未指定'}</Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Match Results */}
      <Card title={`匹配结果 (${matchResults.length} 人)`}>
        <Spin spinning={loading}>
          {matchResults.length > 0 ? (
            <Table
              dataSource={matchResults}
              columns={columns}
              rowKey="talent_id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 位候选人`,
              }}
              scroll={{ x: 1400 }}
            />
          ) : (
            <Empty
              description='请输入职位描述并点击"智能匹配"开始搜索'
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default JDMatchPage

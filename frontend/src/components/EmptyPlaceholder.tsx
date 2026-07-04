import { Empty, Button, Space, Typography } from 'antd'

const { Text, Title } = Typography

interface EmptyPlaceholderProps {
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

const EmptyPlaceholder: React.FC<EmptyPlaceholderProps> = ({
  title = '暂无数据',
  description,
  action,
}) => {
  return (
    <Empty
      style={{ padding: 48 }}
      description={
        <Space direction="vertical" size={8}>
          <Title level={5} style={{ margin: 0 }}>
            {title}
          </Title>
          {description && <Text type="secondary">{description}</Text>}
          {action && (
            <Button type="primary" onClick={action.onClick}>
              {action.label}
            </Button>
          )}
        </Space>
      }
    />
  )
}

export default EmptyPlaceholder

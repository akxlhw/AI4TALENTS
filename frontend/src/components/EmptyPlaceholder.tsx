import { Empty, Button, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

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
  title,
  description,
  action,
}) => {
  const { t } = useTranslation('common')
  const resolvedTitle = title ?? t('status.empty')

  return (
    <Empty
      style={{ padding: 48 }}
      description={
        <Space direction="vertical" size={8}>
          <Title level={5} style={{ margin: 0 }}>
            {resolvedTitle}
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

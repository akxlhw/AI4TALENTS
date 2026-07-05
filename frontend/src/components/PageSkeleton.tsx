import { Skeleton, Card, Row, Col } from 'antd'

const PageSkeleton: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Skeleton active paragraph={{ rows: 0 }} title={{ width: 300 }} />
      <Row gutter={16} style={{ marginTop: 24 }}>
        {[1, 2, 3].map(i => (
          <Col xs={24} sm={8} key={i}>
            <Card>
              <Skeleton active avatar paragraph={{ rows: 1 }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    </div>
  )
}

export default PageSkeleton

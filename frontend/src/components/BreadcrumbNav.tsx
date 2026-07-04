import { Breadcrumb } from 'antd'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem {
  label: string
  path?: string
}

interface BreadcrumbNavProps {
  items: BreadcrumbItem[]
}

const BreadcrumbNav: React.FC<BreadcrumbNavProps> = ({ items }) => {
  return (
    <Breadcrumb style={{ marginBottom: 16 }}>
      {items.map((item, index) => (
        <Breadcrumb.Item key={index}>
          {item.path && index < items.length - 1 ? (
            <Link to={item.path}>{item.label}</Link>
          ) : (
            item.label
          )}
        </Breadcrumb.Item>
      ))}
    </Breadcrumb>
  )
}

export default BreadcrumbNav

/**
 * SearchTemplateModal - 搜索模板保存弹窗组件
 */
import { Modal, Input, Typography } from 'antd'
import type { SearchFilterValues } from './SearchFilterPanel'

const { Text } = Typography

export interface SearchTemplateModalProps {
  visible: boolean
  templateName: string
  filters: SearchFilterValues
  onNameChange: (name: string) => void
  onOk: () => void
  onCancel: () => void
}

const SearchTemplateModal: React.FC<SearchTemplateModalProps> = ({
  visible,
  templateName,
  filters,
  onNameChange,
  onOk,
  onCancel,
}) => {
  const filterSummary = [
    filters.role && `角色=${filters.role}`,
    filters.tech_domain_id && `技术领域`,
    filters.country_id && `国家`,
    filters.school_id && `学校`,
    filters.min_works && `论文≥${filters.min_works}`,
    filters.min_citations && `引用≥${filters.min_citations}`,
  ].filter(Boolean).join(', ') || '无'

  return (
    <Modal
      title="保存搜索模板"
      open={visible}
      onOk={onOk}
      onCancel={onCancel}
      okText="保存"
      cancelText="取消"
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">将保存当前的筛选条件和排序设置</Text>
      </div>
      <Input
        placeholder="输入模板名称..."
        value={templateName}
        onChange={(e) => onNameChange(e.target.value)}
        onPressEnter={onOk}
      />
      <div style={{ marginTop: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          当前筛选: {filterSummary}
        </Text>
      </div>
    </Modal>
  )
}

export default SearchTemplateModal

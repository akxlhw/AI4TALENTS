import { Tabs } from 'antd'
import AcademicEmbeddingPanel from './academic-embedding-panel'
import type { AcademicEmbeddingPanelProps } from './academic-embedding-panel'
import OsEmbeddingPanel from './os-embedding-panel'
import type { OsEmbeddingPanelProps } from './os-embedding-panel'

interface EmbeddingPanelProps {
  academicProps: AcademicEmbeddingPanelProps
  osProps: OsEmbeddingPanelProps
}

const EmbeddingPanel: React.FC<EmbeddingPanelProps> = ({ academicProps, osProps }) => {
  return (
    <Tabs
      type="card"
      items={[
        {
          key: 'academic',
          label: '学术人才库',
          children: <AcademicEmbeddingPanel {...academicProps} />,
        },
        {
          key: 'open-source',
          label: '开源人才库',
          children: <OsEmbeddingPanel {...osProps} />,
        },
      ]}
    />
  )
}

export default EmbeddingPanel

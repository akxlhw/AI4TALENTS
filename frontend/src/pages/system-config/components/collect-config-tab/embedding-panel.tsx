import { Tabs } from 'antd'
import { useTranslation } from 'react-i18next'
import '../../../../i18n/namespaces/system-config'
import AcademicEmbeddingPanel from './academic-embedding-panel'
import type { AcademicEmbeddingPanelProps } from './academic-embedding-panel'
import OsEmbeddingPanel from './os-embedding-panel'
import type { OsEmbeddingPanelProps } from './os-embedding-panel'

interface EmbeddingPanelProps {
  academicProps: AcademicEmbeddingPanelProps
  osProps: OsEmbeddingPanelProps
}

const EmbeddingPanel: React.FC<EmbeddingPanelProps> = ({ academicProps, osProps }) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  return (
    <Tabs
      type="card"
      items={[
        {
          key: 'academic',
          label: t('collectConfig.embeddings.academicTab'),
          children: <AcademicEmbeddingPanel {...academicProps} />,
        },
        {
          key: 'open-source',
          label: t('collectConfig.embeddings.osTab'),
          children: <OsEmbeddingPanel {...osProps} />,
        },
      ]}
    />
  )
}

export default EmbeddingPanel

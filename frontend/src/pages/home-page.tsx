import { useDomainStore } from '../stores/domainStore'
import AcademicHomePage from './academic/academic-home-page'
import OpenSourcePage from './open-source/open-source-page'
import LabOverviewPage from './lab/lab-overview-page'

/* ── Home Page Dispatcher ── */
const HomePage: React.FC = () => {
  const { currentDomain } = useDomainStore()

  if (currentDomain === 'opensource') {
    return <OpenSourcePage />
  }

  if (currentDomain === 'lab') {
    return <LabOverviewPage />
  }

  return <AcademicHomePage />
}

export default HomePage

import { useDomainStore } from '../stores/domainStore'
import AcademicHomePage from './academic/academic-home-page'
import OpenSourcePage from './open-source/open-source-page'

/* ── Home Page Dispatcher ── */
const HomePage: React.FC = () => {
  const { currentDomain } = useDomainStore()

  if (currentDomain === 'opensource') {
    return <OpenSourcePage />
  }

  return <AcademicHomePage />
}

export default HomePage

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/home-page'
import SearchRecommendPage from './pages/academic/academic-search-page'
import TalentDetailPage from './pages/academic/academic-talent-detail-page'
import SchoolDetailPage from './pages/academic/academic-school-detail-page'
import LoginPage from './pages/auth/login-page'
import RegisterPage from './pages/auth/register-page'
import PrivacyPolicyPage from './pages/legal/privacy-policy-page'
import TermsOfUsePage from './pages/legal/terms-of-use-page'
import StorageConsentBanner from './components/StorageConsentBanner'
import AdminPage from './pages/admin/admin-page'
import AuditLogPage from './pages/admin/audit-log-page'
import FavoritesPage from './pages/user/favorites-page'
import ProfilePage from './pages/user/profile-page'
import TechDomainPage from './pages/academic/academic-tech-domain-page'
import CountrySchoolPage from './pages/academic/academic-country-school-page'
import SystemConfigPage from './pages/system-config/system-config-page'
import DataVersionPage from './pages/admin/data-version-page'
import OpenSourceDemoPage from './pages/open-source/open-source-demo-page'
import OpenSourcePage from './pages/open-source/open-source-page'
import OpenSourceSearchPage from './pages/open-source/open-source-search-page'
import DeveloperDetailPage from './pages/open-source/open-source-developer-detail-page'
import RepoDetailPage from './pages/open-source/repo-detail-page'
import RepoListPage from './pages/open-source/repo-list-page'
import CompetitionDemoPage from './pages/competition/competition-demo-page'
import IndustryDemoPage from './pages/industry/industry-demo-page'
import FeedbackPage from './pages/feedback/feedback-page'
import SuggestionAdminPage from './pages/admin/suggestion-admin-page'
import { useAuth } from './contexts/AuthContext'

// Protected Route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

// Super Admin Route component (super_admin only)
const SuperAdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.role !== 'super_admin') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

// Public Route - redirect to home if already logged in
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />
      <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
      <Route path="/terms-of-use" element={<TermsOfUsePage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="tech-domain" element={<TechDomainPage />} />
        <Route path="country-school" element={<CountrySchoolPage />} />
        <Route path="search-recommend" element={<SearchRecommendPage />} />
        <Route path="search" element={<Navigate to="/search-recommend" replace />} />
        <Route path="jd-match" element={<Navigate to="/search-recommend?tab=recommend&mode=jd-match" replace />} />
        <Route path="recommend" element={<Navigate to="/search-recommend?tab=recommend&mode=similar" replace />} />
        <Route path="demo-opensource" element={<OpenSourceDemoPage />} />
        <Route path="opensource" element={<OpenSourcePage />} />
        <Route path="opensource/search" element={<OpenSourceSearchPage />} />
        <Route path="opensource/developers/:id" element={<DeveloperDetailPage />} />
        <Route path="opensource/repos" element={<RepoListPage />} />
        <Route path="opensource/repos/:owner/:name" element={<RepoDetailPage />} />
        <Route path="demo-competition" element={<CompetitionDemoPage />} />
        <Route path="demo-industry" element={<IndustryDemoPage />} />
        <Route path="talents/:id" element={<TalentDetailPage />} />
        <Route path="schools/:id" element={<SchoolDetailPage />} />
        <Route path="favorites" element={<FavoritesPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route
          path="admin"
          element={
            <SuperAdminRoute>
              <AdminPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="system-config"
          element={
            <SuperAdminRoute>
              <SystemConfigPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="collect"
          element={
            <Navigate to="/system-config" replace />
          }
        />
        <Route
          path="data-version"
          element={
            <SuperAdminRoute>
              <DataVersionPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="audit-logs"
          element={
            <SuperAdminRoute>
              <AuditLogPage />
            </SuperAdminRoute>
          }
        />
        <Route path="feedback" element={<FeedbackPage />} />
        <Route
          path="suggestion-admin"
          element={
            <SuperAdminRoute>
              <SuggestionAdminPage />
            </SuperAdminRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <StorageConsentBanner />
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App

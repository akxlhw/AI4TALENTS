import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'
import SearchRecommendPage from './pages/SearchRecommendPage'
import TalentDetailPage from './pages/TalentDetailPage'
import SchoolDetailPage from './pages/SchoolDetailPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import AdminPage from './pages/AdminPage'
import AuditLogPage from './pages/AuditLogPage'
import FavoritesPage from './pages/FavoritesPage'
import ProfilePage from './pages/ProfilePage'
import TechDomainPage from './pages/TechDomainPage'
import CountrySchoolPage from './pages/CountrySchoolPage'
import SystemConfigPage from './pages/SystemConfigPage'
import DataVersionPage from './pages/DataVersionPage'
import OpenSourceDemoPage from './pages/OpenSourceDemoPage'
import CompetitionDemoPage from './pages/CompetitionDemoPage'
import IndustryDemoPage from './pages/IndustryDemoPage'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { FavoritesProvider } from './contexts/FavoritesContext'

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

// Admin Route component
const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading, isAdmin } = useAuth()

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

  if (!isAdmin) {
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
        <Route path="demo-competition" element={<CompetitionDemoPage />} />
        <Route path="demo-industry" element={<IndustryDemoPage />} />
        <Route path="talents/:id" element={<TalentDetailPage />} />
        <Route path="schools/:id" element={<SchoolDetailPage />} />
        <Route path="favorites" element={<FavoritesPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route
          path="admin"
          element={
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          }
        />
        <Route
          path="system-config"
          element={
            <AdminRoute>
              <SystemConfigPage />
            </AdminRoute>
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
            <AdminRoute>
              <DataVersionPage />
            </AdminRoute>
          }
        />
        <Route
          path="audit-logs"
          element={
            <AdminRoute>
              <AuditLogPage />
            </AdminRoute>
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
      <AuthProvider>
        <FavoritesProvider>
          <AppRoutes />
        </FavoritesProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App

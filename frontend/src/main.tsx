import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { RequireAuth } from './components/RequireAuth'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { GroupDetailPage } from './pages/GroupDetailPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/groups/:id" element={<GroupDetailPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)

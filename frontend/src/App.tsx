import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import MainLayout from '@/components/layout/MainLayout'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Animals from '@/pages/Animals'
import Paddocks from '@/pages/Paddocks'
import Devices from '@/pages/Devices'
import Alerts from '@/pages/Alerts'
import Health from '@/pages/Health'
import Reproduction from '@/pages/Reproduction'
import Weights from '@/pages/Weights'
import MapPage from '@/pages/MapPage'
import NOC from '@/pages/NOC'
import Lora from '@/pages/Lora'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="animals" element={<Animals />} />
          <Route path="paddocks" element={<Paddocks />} />
          <Route path="devices" element={<Devices />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="health" element={<Health />} />
          <Route path="reproduction" element={<Reproduction />} />
          <Route path="weights" element={<Weights />} />
          <Route path="map" element={<MapPage />} />
          <Route path="noc" element={<NOC />} />
          <Route path="lora" element={<Lora />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

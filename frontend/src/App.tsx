import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import CostDetail from './pages/CostDetail'
import RulesManagement from './pages/RulesManagement'
import AlertSettings from './pages/AlertSettings'
import AwsSettings from './pages/AwsSettings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="costs" element={<CostDetail />} />
          <Route path="rules" element={<RulesManagement />} />
          <Route path="alerts" element={<AlertSettings />} />
          <Route path="aws-settings" element={<AwsSettings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

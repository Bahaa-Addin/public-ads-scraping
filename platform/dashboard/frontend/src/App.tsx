import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import TemplateLayout from './components/TemplateLayout'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Assets from './pages/Assets'
import Scrapers from './pages/Scrapers'
import Analytics from './pages/Analytics'
import Logs from './pages/Logs'
import Settings from './pages/Settings'
import Pipeline from './pages/Pipeline'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing page */}
        <Route path="/" element={<Landing />} />
        
        {/* Real dashboard routes (live data) */}
        <Route element={<Layout />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="pipeline" element={<Pipeline />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="assets" element={<Assets />} />
          <Route path="scrapers" element={<Scrapers />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="logs" element={<Logs />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Template dashboard routes (demo/mock data) */}
        <Route path="/template" element={<TemplateLayout />}>
          <Route index element={<Navigate to="/template/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="pipeline" element={<Pipeline />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="assets" element={<Assets />} />
          <Route path="scrapers" element={<Scrapers />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="logs" element={<Logs />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

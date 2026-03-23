import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useTelegram } from '@/hooks/useTelegram'
import { useAppSettings } from '@/hooks/useAppSettings'
import Dashboard from '@/components/Dashboard'
import Transactions from '@/components/Transactions'
import Transfers from '@/components/Transfers'
import Statistics from '@/components/Statistics'
import Settings from '@/components/Settings'
import Debts from '@/components/Debts'
import { AdminPanel } from '@/components/AdminPanel'
import Workers from '@/components/Workers'
import BottomNav from '@/components/shared/BottomNav'
import { LoadingState } from '@/components/shared/States'

function App() {
  const { webApp, user } = useTelegram()
  const [isReady, setIsReady] = useState(false)
  const allowDevPreview = import.meta.env.DEV && !webApp
  const { settings, theme, isLoading } = useAppSettings()

  useEffect(() => {
    if (webApp) {
      webApp.expand()
      webApp.enableClosingConfirmation()
      webApp.setHeaderColor(theme === 'dark' ? '#0b0b0b' : '#f4f4f2')
      webApp.setBackgroundColor(theme === 'dark' ? '#090909' : '#f4f4f2')
      webApp.ready()
    }
    setIsReady(true)
  }, [theme, webApp])

  if (!isReady || isLoading || (!user && !allowDevPreview)) {
    return (
      <div className="app-shell">
        <div className="app-content">
          <LoadingState label="Loading..." />
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <div className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/transfers" element={<Transfers />} />
            <Route path="/debts" element={<Debts />} />
            <Route path="/team" element={<Workers />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <BottomNav canSeeTeam={Boolean(settings?.is_group_admin || settings?.is_admin)} />
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App

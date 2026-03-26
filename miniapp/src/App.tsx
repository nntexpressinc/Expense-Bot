import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
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

function ScrollToTop() {
  const location = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    const appShell = document.querySelector('.app-shell') as HTMLElement | null
    const appContent = document.querySelector('.app-content') as HTMLElement | null
    appShell?.scrollTo({ top: 0, behavior: 'auto' })
    appContent?.scrollTo({ top: 0, behavior: 'auto' })
  }, [location.pathname])

  return null
}

function App() {
  const { webApp, user, authReady } = useTelegram()
  const [isReady, setIsReady] = useState(false)
  const allowDevPreview = import.meta.env.DEV && !webApp
  const { settings, theme, isLoading } = useAppSettings(allowDevPreview || authReady)
  const canManageAdmin = Boolean(settings?.is_group_admin || settings?.is_admin)
  const routerBase = import.meta.env.BASE_URL.replace(/\/$/, '') || '/'

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

  if (!isReady || (webApp && !authReady && !allowDevPreview) || isLoading || (!user && !allowDevPreview)) {
    return (
      <div className="app-shell">
        <div className="app-content">
          <LoadingState label="Loading..." />
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter basename={routerBase}>
      <div className="app-shell">
        <div className="app-content">
          <ScrollToTop />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/transfers" element={<Transfers />} />
            <Route path="/debts" element={<Debts />} />
            <Route path="/team" element={<Workers />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin" element={canManageAdmin ? <AdminPanel /> : <Navigate to="/settings" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <BottomNav />
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App

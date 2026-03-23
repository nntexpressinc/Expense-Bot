import { Link, useLocation } from 'react-router-dom'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { useAppSettings } from '@/hooks/useAppSettings'

const iconClass = 'h-[18px] w-[18px]'

const Icon = ({ name }: { name: 'home' | 'activity' | 'transfers' | 'debts' | 'settings' }) => {
  if (name === 'home') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={iconClass}>
        <path d="M4 10.5 12 4l8 6.5" />
        <path d="M6.5 9.5V20h11V9.5" />
      </svg>
    )
  }
  if (name === 'activity') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={iconClass}>
        <rect x="5" y="4" width="14" height="16" rx="2" />
        <path d="M8 9h8M8 13h8M8 17h5" />
      </svg>
    )
  }
  if (name === 'transfers') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={iconClass}>
        <path d="M4 8h12" />
        <path d="m13 5 3 3-3 3" />
        <path d="M20 16H8" />
        <path d="m11 13-3 3 3 3" />
      </svg>
    )
  }
  if (name === 'debts') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={iconClass}>
        <rect x="4" y="6" width="16" height="12" rx="2" />
        <path d="M8 10h8M8 14h5" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={iconClass}>
      <path d="M12 8.75A3.25 3.25 0 1 0 12 15.25A3.25 3.25 0 1 0 12 8.75Z" />
      <path d="m3.5 13.5 1.8.3a7.1 7.1 0 0 0 .6 1.5l-1.1 1.5 1.7 1.7 1.5-1.1c.5.3 1 .5 1.6.7l.3 1.8h2.4l.3-1.8c.6-.1 1.1-.3 1.6-.7l1.5 1.1 1.7-1.7-1.1-1.5c.3-.5.5-1 .6-1.5l1.8-.3v-2.4l-1.8-.3a7.1 7.1 0 0 0-.6-1.5l1.1-1.5-1.7-1.7-1.5 1.1a7.1 7.1 0 0 0-1.6-.7l-.3-1.8h-2.4l-.3 1.8c-.6.1-1.1.3-1.6.7l-1.5-1.1-1.7 1.7 1.1 1.5a7.1 7.1 0 0 0-.6 1.5l-1.8.3v2.4Z" />
    </svg>
  )
}

export default function BottomNav() {
  const location = useLocation()
  const { haptic } = useTelegram()
  const { language } = useAppSettings()

  const items = [
    { path: '/', label: t('home', language), icon: 'home' as const },
    { path: '/transactions', label: t('activity', language), icon: 'activity' as const },
    { path: '/transfers', label: t('transfers', language), icon: 'transfers' as const },
    { path: '/debts', label: t('debts', language), icon: 'debts' as const },
    { path: '/settings', label: t('settings', language), icon: 'settings' as const },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 px-3 pb-[calc(10px+env(safe-area-inset-bottom,0px))]">
      <div
        className="mx-auto flex max-w-[460px] items-center rounded-[26px] border px-1 py-1 shadow-lg backdrop-blur"
        style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
      >
        {items.map((item) => {
          const active = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => haptic.selection()}
              className="flex min-h-[62px] flex-1 flex-col items-center justify-center rounded-[22px] transition-colors"
              style={{
                background: active ? 'var(--accent)' : 'transparent',
                color: active ? 'var(--accent-contrast)' : 'var(--text-soft)',
              }}
            >
              <Icon name={item.icon} />
              <span className="mt-1 text-[11px] font-medium">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

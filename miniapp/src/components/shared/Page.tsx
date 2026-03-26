import { PropsWithChildren, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppSettings } from '@/hooks/useAppSettings'
import { t } from '@/i18n'

export const Page = ({ title, subtitle, actions, children }: PropsWithChildren<{ title: string; subtitle?: string; actions?: ReactNode }>) => {
  const navigate = useNavigate()
  const { settings, language, stopImpersonation } = useAppSettings()
  const actingAsName = `${settings?.first_name || ''} ${settings?.last_name || ''}`.trim() || settings?.username || settings?.id

  return (
    <div className="page-stack">
      {settings?.is_impersonating ? (
        <section className="surface-card border border-[var(--border-strong)] px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--text)]">
                {t('actingAs', language)}: {actingAsName}
              </p>
              <p className="mt-1 text-xs text-[var(--text-soft)]">
                {t('actingAsHint', language)} {settings.actor_display_name || '-'}
              </p>
            </div>
            <button
              type="button"
              className="secondary-button !px-3 !py-2 text-xs"
              onClick={async () => {
                await stopImpersonation()
                navigate('/admin', { replace: true })
              }}
            >
              {t('exitImpersonation', language)}
            </button>
          </div>
        </section>
      ) : null}
      <header className="surface-card px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-[24px] font-semibold tracking-tight text-[var(--text)]">{title}</h1>
            {subtitle ? <p className="mt-1 text-sm text-[var(--text-soft)]">{subtitle}</p> : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </div>
      </header>
      {children}
    </div>
  )
}

export const Card = ({ children, className = '' }: PropsWithChildren<{ className?: string }>) => (
  <section className={`surface-card px-4 py-4 ${className}`.trim()}>{children}</section>
)

export const SectionTitle = ({ title, hint }: { title: string; hint?: string }) => (
  <div className="mb-3 flex flex-col items-start gap-1 sm:flex-row sm:items-end sm:justify-between">
    <h2 className="text-base font-semibold leading-tight text-[var(--text)]">{title}</h2>
    {hint ? <span className="text-xs text-[var(--text-muted)]">{hint}</span> : null}
  </div>
)

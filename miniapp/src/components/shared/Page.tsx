import { PropsWithChildren, ReactNode } from 'react'

export const Page = ({ title, subtitle, actions, children }: PropsWithChildren<{ title: string; subtitle?: string; actions?: ReactNode }>) => (
  <div className="page-stack">
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

export const Card = ({ children, className = '' }: PropsWithChildren<{ className?: string }>) => (
  <section className={`surface-card px-4 py-4 ${className}`.trim()}>{children}</section>
)

export const SectionTitle = ({ title, hint }: { title: string; hint?: string }) => (
  <div className="mb-3 flex items-end justify-between gap-3">
    <h2 className="text-base font-semibold text-[var(--text)]">{title}</h2>
    {hint ? <span className="text-xs text-[var(--text-muted)]">{hint}</span> : null}
  </div>
)

export const LoadingState = ({ label }: { label: string }) => (
  <div className="flex min-h-[40vh] items-center justify-center">
    <div className="flex flex-col items-center gap-3 text-[var(--text-soft)]">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-[var(--border-strong)] border-t-[var(--accent)]" />
      <p className="text-sm">{label}</p>
    </div>
  </div>
)

export const EmptyState = ({ title, hint }: { title: string; hint?: string }) => (
  <div className="surface-card px-4 py-5">
    <p className="text-sm font-medium text-[var(--text)]">{title}</p>
    {hint ? <p className="mt-1 text-sm text-[var(--text-soft)]">{hint}</p> : null}
  </div>
)

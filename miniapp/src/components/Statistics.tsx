import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { exportStatisticsExcel, getStatistics } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

export default function Statistics() {
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month')

  const statsQuery = useQuery({
    queryKey: ['statistics', period],
    queryFn: () => getStatistics(period),
  })

  const handleExport = async () => {
    try {
      const blob = await exportStatisticsExcel(period)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `statistics-${period}.xlsx`
      link.click()
      window.URL.revokeObjectURL(url)
      haptic.success()
    } catch (error: any) {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    }
  }

  if (statsQuery.isLoading && !statsQuery.data) {
    return <LoadingState label={t('loading', language)} />
  }

  if (!statsQuery.data) {
    return <EmptyState title={t('notLoaded', language)} />
  }

  const stats = statsQuery.data
  const displayCurrency = settings?.default_currency || 'UZS'

  return (
    <Page
      title={t('statistics', language)}
      subtitle={settings?.active_group_name || '-'}
      actions={
        <button type="button" className="secondary-button" onClick={() => void handleExport()}>
          {t('exportExcel', language)}
        </button>
      }
    >
      <Card>
        <SectionTitle title={t('choosePeriod', language)} />
        <div className="flex flex-wrap gap-2">
          {(['day', 'week', 'month', 'year'] as const).map((value) => (
            <button key={value} type="button" className={`pill-button ${period === value ? 'active' : ''}`} onClick={() => setPeriod(value)}>
              {t(value, language)}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle title={stats.period} hint={displayCurrency} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('income', language)}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">{formatMoney(stats.total_income, displayCurrency, locale)}</p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('expense', language)}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">{formatMoney(stats.total_expense, displayCurrency, locale)}</p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">Net</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">{formatMoney(stats.difference, displayCurrency, locale)}</p>
          </div>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('statistics', language)} hint="Top categories" />
        {stats.top_categories.length ? (
          <div className="space-y-3">
            {stats.top_categories.map((category, index) => (
              <div key={`${category.name}-${index}`} className="surface-card-muted px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">
                      {category.icon} {category.name}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">{category.percent.toFixed(1)}%</p>
                  </div>
                  <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(category.amount, displayCurrency, locale)}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={t('noOperations', language)} />
        )}
      </Card>
    </Page>
  )
}

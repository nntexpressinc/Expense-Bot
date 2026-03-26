import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { exportStatisticsExcel, getStatistics, type Statistics, type StatisticsParams, type StatisticsPeriod } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

export default function Statistics() {
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [period, setPeriod] = useState<StatisticsPeriod>('month')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const hasInvalidRange = period === 'custom' && Boolean(dateFrom) && Boolean(dateTo) && dateFrom > dateTo
  const isCustomReady = period !== 'custom' || (Boolean(dateFrom) && Boolean(dateTo))
  const statsParams: StatisticsParams = period === 'custom'
    ? { period, date_from: dateFrom || undefined, date_to: dateTo || undefined }
    : { period }

  const statsQuery = useQuery({
    queryKey: ['statistics', period, dateFrom, dateTo],
    queryFn: () => getStatistics(statsParams),
    enabled: isCustomReady && !hasInvalidRange,
  })

  const handleExport = async () => {
    if (!isCustomReady || hasInvalidRange) {
      await showAlert(t('selectDateRange', language))
      return
    }
    try {
      const { blob, filename } = await exportStatisticsExcel(statsParams)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
      haptic.success()
    } catch (error: any) {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    }
  }

  const stats = statsQuery.data as Statistics | undefined
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
          {(['day', 'week', 'month', 'year', 'custom'] as const).map((value) => (
            <button key={value} type="button" className={`pill-button ${period === value ? 'active' : ''}`} onClick={() => setPeriod(value)}>
              {t(value, language)}
            </button>
          ))}
        </div>
        {period === 'custom' ? (
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-[var(--text)]">{t('fromDate', language)}</span>
              <input type="date" className="field" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-[var(--text)]">{t('toDate', language)}</span>
              <input type="date" className="field" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </label>
            <p className="text-sm text-[var(--text-soft)] sm:col-span-2">{t('customDateHint', language)}</p>
          </div>
        ) : null}
      </Card>

      {period === 'custom' && (!isCustomReady || hasInvalidRange) ? (
        <Card>
          <EmptyState title={t('selectDateRange', language)} />
        </Card>
      ) : null}

      {statsQuery.isLoading && !stats ? (
        <LoadingState label={t('loading', language)} />
      ) : stats ? (
        <>
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
                <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('net', language)}</p>
                <p className="mt-2 text-lg font-semibold text-[var(--text)]">{formatMoney(stats.difference, displayCurrency, locale)}</p>
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle title={t('statistics', language)} hint={t('topCategories', language)} />
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
        </>
      ) : period !== 'custom' ? (
        <EmptyState title={t('notLoaded', language)} />
      ) : null}
    </Page>
  )
}

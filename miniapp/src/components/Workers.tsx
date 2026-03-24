import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAttendance,
  createWorker,
  createWorkerAdvance,
  createWorkerPayment,
  getWorkersSummary,
  listAttendanceEntries,
  listWorkers,
} from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

const monthBounds = () => {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  const toIso = (date: Date) => date.toISOString().slice(0, 10)
  return { start: toIso(start), end: toIso(end) }
}

const workerCopy = {
  uz: {
    todayPresent: '\u2705 Bugun keldi',
    todayMarked: '\u2705 Bugun belgilangan',
    attendanceMissing: 'Bugungi davomat hali belgilanmagan',
    attendanceSaved: 'Bugungi davomat saqlangan',
    payFromBalance: "To'lov asosiy balansdan yechiladi",
    optionalRole: 'Vazifa (ixtiyoriy)',
    volumeHint: 'Bugungi birlikni kiriting',
  },
  ru: {
    todayPresent: '\u2705 \u041e\u0442\u043c\u0435\u0442\u0438\u0442\u044c \u043f\u0440\u0438\u0445\u043e\u0434 \u0441\u0435\u0433\u043e\u0434\u043d\u044f',
    todayMarked: '\u2705 \u041d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u0443\u0436\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e',
    attendanceMissing: '\u0421\u0435\u0433\u043e\u0434\u043d\u044f\u0448\u043d\u044f\u044f \u043f\u043e\u0441\u0435\u0449\u0430\u0435\u043c\u043e\u0441\u0442\u044c \u0435\u0449\u0451 \u043d\u0435 \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u0430',
    attendanceSaved: '\u0421\u0435\u0433\u043e\u0434\u043d\u044f\u0448\u043d\u044f\u044f \u043f\u043e\u0441\u0435\u0449\u0430\u0435\u043c\u043e\u0441\u0442\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430',
    payFromBalance: '\u0412\u044b\u043f\u043b\u0430\u0442\u0430 \u0441\u043f\u0438\u0448\u0435\u0442\u0441\u044f \u0441 \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0433\u043e \u0431\u0430\u043b\u0430\u043d\u0441\u0430',
    optionalRole: '\u0420\u043e\u043b\u044c (\u043d\u0435\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e)',
    volumeHint: '\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043e\u0431\u044a\u0451\u043c \u0437\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f',
  },
  en: {
    todayPresent: '\u2705 Mark present today',
    todayMarked: '\u2705 Already marked for today',
    attendanceMissing: 'Today attendance is not marked yet',
    attendanceSaved: 'Today attendance is saved',
    payFromBalance: 'Payment is deducted from main balance',
    optionalRole: 'Role (optional)',
    volumeHint: 'Enter today units',
  },
} as const

export default function Workers() {
  const queryClient = useQueryClient()
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [fullName, setFullName] = useState('')
  const [roleName, setRoleName] = useState('')
  const [paymentType, setPaymentType] = useState<'daily' | 'monthly' | 'volume'>('daily')
  const [rate, setRate] = useState('')
  const [volumeUnits, setVolumeUnits] = useState<Record<string, string>>({})
  const [advanceAmount, setAdvanceAmount] = useState<Record<string, string>>({})
  const [paymentAmount, setPaymentAmount] = useState<Record<string, string>>({})

  const month = useMemo(monthBounds, [])
  const copy = workerCopy[language]

  const workersQuery = useQuery({
    queryKey: ['workers'],
    queryFn: () => listWorkers({ include_inactive: false }),
  })
  const summaryQuery = useQuery({
    queryKey: ['workers-summary', month.start, month.end],
    queryFn: () => getWorkersSummary({ start_date: month.start, end_date: month.end }),
  })
  const attendanceQuery = useQuery({
    queryKey: ['workers-attendance', month.start, month.end],
    queryFn: () => listAttendanceEntries({ start_date: month.start, end_date: month.end, limit: 80 }),
  })

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['workers'] }),
      queryClient.invalidateQueries({ queryKey: ['workers-summary'] }),
      queryClient.invalidateQueries({ queryKey: ['workers-attendance'] }),
      queryClient.invalidateQueries({ queryKey: ['balance'] }),
    ])
  }

  const handleError = async (error: any) => {
    haptic.error()
    await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
  }

  const createWorkerMutation = useMutation({
    mutationFn: createWorker,
    onSuccess: async () => {
      await refresh()
      setFullName('')
      setRoleName('')
      setRate('')
      setPaymentType('daily')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const attendanceMutation = useMutation({
    mutationFn: ({ workerId, status, units }: { workerId: string; status: 'present' | 'custom'; units: number }) =>
      createAttendance(workerId, {
        entry_date: new Date().toISOString().slice(0, 10),
        status,
        units,
        comment: undefined,
      }),
    onSuccess: async () => {
      await refresh()
      haptic.success()
    },
    onError: handleError,
  })

  const advanceMutation = useMutation({
    mutationFn: ({ workerId, amount }: { workerId: string; amount: number }) =>
      createWorkerAdvance(workerId, {
        amount,
        currency: (settings?.default_currency || 'UZS') as 'UZS' | 'USD',
        payment_date: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: async () => {
      await refresh()
      haptic.success()
    },
    onError: handleError,
  })

  const paymentMutation = useMutation({
    mutationFn: ({ workerId, amount }: { workerId: string; amount: number }) =>
      createWorkerPayment(workerId, {
        amount,
        currency: (settings?.default_currency || 'UZS') as 'UZS' | 'USD',
        payment_date: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: async () => {
      await refresh()
      haptic.success()
    },
    onError: handleError,
  })

  if (!settings?.is_group_admin && !settings?.is_admin) {
    return (
      <Page title={t('team', language)} subtitle={settings?.active_group_name || '-'}>
        <EmptyState title={t('notAllowed', language)} />
      </Page>
    )
  }

  if ((workersQuery.isLoading && !workersQuery.data) || (summaryQuery.isLoading && !summaryQuery.data)) {
    return <LoadingState label={t('loading', language)} />
  }

  const workerSummaryMap = new Map((summaryQuery.data?.workers || []).map((worker) => [worker.worker_id, worker]))
  const totals = summaryQuery.data?.totals
  const attendanceItems = attendanceQuery.data || []
  const markedTodayCount = workersQuery.data?.filter((worker) => worker.today_status).length || 0

  const submitWorker = async (event: FormEvent) => {
    event.preventDefault()
    const numericRate = Number(rate)
    if (!fullName.trim() || !numericRate || numericRate <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }

    await createWorkerMutation.mutateAsync({
      full_name: fullName.trim(),
      role_name: roleName.trim() || undefined,
      payment_type: paymentType,
      rate: numericRate,
      currency: (settings?.default_currency || 'UZS') as 'UZS' | 'USD',
      start_date: new Date().toISOString().slice(0, 10),
    })
  }

  const markTodayPresent = async (workerId: string) => {
    await attendanceMutation.mutateAsync({ workerId, status: 'present', units: 1 })
  }

  const saveVolumeUnits = async (workerId: string) => {
    const units = Number(volumeUnits[workerId] || 0)
    if (!units || units <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await attendanceMutation.mutateAsync({ workerId, status: 'custom', units })
    setVolumeUnits((current) => ({ ...current, [workerId]: '' }))
  }

  const saveAdvance = async (workerId: string) => {
    const amountValue = Number(advanceAmount[workerId] || 0)
    if (!amountValue || amountValue <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await advanceMutation.mutateAsync({ workerId, amount: amountValue })
    setAdvanceAmount((current) => ({ ...current, [workerId]: '' }))
  }

  const savePayment = async (workerId: string, payableAmount: number) => {
    const amountValue = Number(paymentAmount[workerId] || payableAmount || 0)
    if (!amountValue || amountValue <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await paymentMutation.mutateAsync({ workerId, amount: amountValue })
    setPaymentAmount((current) => ({ ...current, [workerId]: '' }))
  }

  return (
    <Page title={t('team', language)} subtitle={settings?.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('workers', language)} hint={`${month.start} - ${month.end}`} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('workers', language)}</p>
            <p className="mt-2 text-xl font-semibold text-[var(--text)]">{workersQuery.data?.length || 0}</p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('attendance', language)}</p>
            <p className="mt-2 text-xl font-semibold text-[var(--text)]">{markedTodayCount}</p>
            <p className="mt-1 text-xs text-[var(--text-soft)]">{t('day', language)}</p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('payable', language)}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">
              {formatMoney(Number(totals?.payable_amount || 0), settings?.default_currency || 'UZS', locale)}
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('addWorker', language)} />
        <form className="space-y-3" onSubmit={submitWorker}>
          <input className="field" placeholder={t('fullName', language)} value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <select className="field" value={paymentType} onChange={(e) => setPaymentType(e.target.value as 'daily' | 'monthly' | 'volume')}>
            <option value="daily">{t('daily', language)}</option>
            <option value="monthly">{t('monthly', language)}</option>
            <option value="volume">{t('volume', language)}</option>
          </select>
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={rate} onChange={(e) => setRate(e.target.value)} />
          <input className="field" placeholder={copy.optionalRole} value={roleName} onChange={(e) => setRoleName(e.target.value)} />
          <button type="submit" className="primary-button w-full" disabled={createWorkerMutation.isPending}>
            {createWorkerMutation.isPending ? t('loading', language) : t('save', language)}
          </button>
        </form>
      </Card>

      <Card>
        <SectionTitle title={t('workers', language)} />
        {workersQuery.data?.length ? (
          <div className="space-y-3">
            {workersQuery.data.map((worker) => {
              const summary = workerSummaryMap.get(worker.id)
              const payableAmount = Number(summary?.payable_amount || 0)
              const attendanceMarked = Boolean(worker.today_status)
              const payButtonLabel = payableAmount > 0
                ? `${t('pay', language)} ${formatMoney(payableAmount, summary?.currency || worker.currency, locale)}`
                : t('pay', language)

              return (
                <div key={worker.id} className="surface-card-muted px-4 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-base font-semibold text-[var(--text)]">{worker.full_name}</p>
                      <p className="mt-1 text-sm text-[var(--text-soft)]">
                        {worker.role_name || '-'} - {t(worker.payment_type as never, language)}
                      </p>
                      <p className="mt-1 text-sm text-[var(--text-soft)]">
                        {formatMoney(Number(worker.rate), worker.currency, locale)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('payable', language)}</p>
                      <p className="mt-2 text-lg font-semibold text-[var(--text)]">
                        {summary ? formatMoney(summary.payable_amount, summary.currency, locale) : '-'}
                      </p>
                    </div>
                  </div>

                  {summary ? (
                    <div className="mt-3 space-y-1 text-sm text-[var(--text-soft)]">
                      <p>{t('advances', language)}: <span className="font-semibold text-[var(--text)]">{formatMoney(Number(summary.advance_amount || 0), summary.currency, locale)}</span></p>
                      <p>{t('payments', language)}: <span className="font-semibold text-[var(--text)]">{formatMoney(Number(summary.paid_amount || 0), summary.currency, locale)}</span></p>
                    </div>
                  ) : null}

                  {worker.payment_type === 'volume' ? (
                    <div className="mt-4 rounded-2xl border border-[var(--border)] px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('attendance', language)}</p>
                      <p className="mt-2 text-sm text-[var(--text-soft)]">{copy.volumeHint}</p>
                      <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
                        <input
                          className="field"
                          inputMode="decimal"
                          placeholder={t('customUnits', language)}
                          value={volumeUnits[worker.id] || ''}
                          onChange={(e) => setVolumeUnits((current) => ({ ...current, [worker.id]: e.target.value }))}
                        />
                        <button type="button" className="primary-button min-w-[110px]" onClick={() => void saveVolumeUnits(worker.id)}>
                          {t('save', language)}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 rounded-2xl border border-[var(--border)] px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('attendance', language)}</p>
                      <p className="mt-2 text-sm text-[var(--text-soft)]">{attendanceMarked ? copy.attendanceSaved : copy.attendanceMissing}</p>
                      <button
                        type="button"
                        className={`${attendanceMarked ? 'secondary-button' : 'primary-button'} mt-3 w-full`}
                        onClick={() => void markTodayPresent(worker.id)}
                      >
                        {attendanceMarked ? copy.todayMarked : copy.todayPresent}
                      </button>
                    </div>
                  )}

                  <div className="mt-4 grid grid-cols-[1fr_auto] gap-2">
                    <input
                      className="field"
                      inputMode="decimal"
                      placeholder={t('advances', language)}
                      value={advanceAmount[worker.id] || ''}
                      onChange={(e) => setAdvanceAmount((current) => ({ ...current, [worker.id]: e.target.value }))}
                    />
                    <button type="button" className="secondary-button min-w-[110px]" onClick={() => void saveAdvance(worker.id)}>
                      {t('recordAdvance', language)}
                    </button>
                  </div>

                  <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
                    <input
                      className="field"
                      inputMode="decimal"
                      placeholder={payableAmount > 0 ? `${payableAmount}` : t('amount', language)}
                      value={paymentAmount[worker.id] || ''}
                      onChange={(e) => setPaymentAmount((current) => ({ ...current, [worker.id]: e.target.value }))}
                    />
                    <button
                      type="button"
                      className="primary-button min-w-[150px]"
                      onClick={() => void savePayment(worker.id, payableAmount)}
                      disabled={payableAmount <= 0}
                    >
                      {payButtonLabel}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-[var(--text-muted)]">{copy.payFromBalance}</p>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState title={t('noWorkers', language)} />
        )}
      </Card>

      <Card>
        <SectionTitle title={t('recentAttendance', language)} hint={`${month.start} - ${month.end}`} />
        {attendanceItems.length ? (
          <div className="space-y-2">
            {attendanceItems.map((entry) => (
              <div key={entry.id} className="surface-card-muted px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{entry.worker_name}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">{entry.entry_date}</p>
                    {entry.comment ? <p className="mt-2 text-sm text-[var(--text-soft)]">{entry.comment}</p> : null}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold capitalize text-[var(--text)]">{entry.status.replace('_', ' ')}</p>
                    {entry.units > 0 ? <p className="mt-1 text-xs text-[var(--text-soft)]">{entry.units}</p> : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={t('attendance', language)} hint={t('retry', language)} />
        )}
      </Card>
    </Page>
  )
}

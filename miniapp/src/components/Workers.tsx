import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAttendance,
  createWorker,
  createWorkerAdvance,
  createWorkerPayment,
  getWorkersSummary,
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
    todayPresent: '? Bugun keldi',
    todayMarked: '? Bugun belgilandi',
    payFromBalance: "To'lov asosiy balansdan yechiladi",
    optionalRole: 'Vazifa (ixtiyoriy)',
  },
  ru: {
    todayPresent: '? Отметить сегодня',
    todayMarked: '? На сегодня отмечено',
    payFromBalance: 'Выплата спишется с основного баланса',
    optionalRole: 'Роль (необязательно)',
  },
  en: {
    todayPresent: '? Mark present today',
    todayMarked: '? Marked for today',
    payFromBalance: 'Payment is deducted from main balance',
    optionalRole: 'Role (optional)',
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

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['workers'] }),
      queryClient.invalidateQueries({ queryKey: ['workers-summary'] }),
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
        <div className="grid grid-cols-2 gap-3">
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('workers', language)}</p>
            <p className="mt-2 text-xl font-semibold text-[var(--text)]">{workersQuery.data?.length || 0}</p>
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
              const dailyMarked = Boolean(worker.today_status)
              const payButtonLabel = payableAmount > 0
                ? `${t('pay', language)} ${formatMoney(payableAmount, summary?.currency || worker.currency, locale)}`
                : t('pay', language)

              return (
                <div key={worker.id} className="surface-card-muted px-4 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-base font-semibold text-[var(--text)]">{worker.full_name}</p>
                      <p className="mt-1 text-sm text-[var(--text-soft)]">
                        {t(worker.payment_type, language)}{worker.role_name ? ` - ${worker.role_name}` : ''}
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

                  {worker.payment_type === 'daily' ? (
                    <button
                      type="button"
                      className={`${dailyMarked ? 'secondary-button' : 'primary-button'} mt-4 w-full`}
                      onClick={() => void markTodayPresent(worker.id)}
                    >
                      {dailyMarked ? copy.todayMarked : copy.todayPresent}
                    </button>
                  ) : null}

                  {worker.payment_type === 'volume' ? (
                    <div className="mt-4 grid grid-cols-[1fr_auto] gap-2">
                      <input
                        className="field"
                        inputMode="decimal"
                        placeholder={t('customUnits', language)}
                        value={volumeUnits[worker.id] || ''}
                        onChange={(e) => setVolumeUnits((current) => ({ ...current, [worker.id]: e.target.value }))}
                      />
                      <button type="button" className="secondary-button min-w-[110px]" onClick={() => void saveVolumeUnits(worker.id)}>
                        {t('save', language)}
                      </button>
                    </div>
                  ) : null}

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
    </Page>
  )
}

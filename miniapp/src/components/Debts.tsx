import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createDebt, listDebts, payDebt } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatDateTime, formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

export default function Debts() {
  const queryClient = useQueryClient()
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [sourceName, setSourceName] = useState('')
  const [sourceContact, setSourceContact] = useState('')
  const [reference, setReference] = useState('')
  const [note, setNote] = useState('')
  const [payAmounts, setPayAmounts] = useState<Record<string, string>>({})

  const debtsQuery = useQuery({
    queryKey: ['debts'],
    queryFn: listDebts,
  })

  const createMutation = useMutation({
    mutationFn: createDebt,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['debts'] }),
        queryClient.invalidateQueries({ queryKey: ['balance'] }),
      ])
      setAmount('')
      setDescription('')
      setSourceName('')
      setSourceContact('')
      setReference('')
      setNote('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: async (error: any) => {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    },
  })

  const payMutation = useMutation({
    mutationFn: ({ debtId, amountValue }: { debtId: string; amountValue: number }) =>
      payDebt(debtId, { amount: amountValue, currency: settings?.default_currency || 'UZS' }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['debts'] }),
        queryClient.invalidateQueries({ queryKey: ['balance'] }),
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
      ])
      setPayAmounts({})
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: async (error: any) => {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    },
  })

  const openDebts = useMemo(
    () => (debtsQuery.data || []).filter((debt) => (debt.remaining || 0) > 0),
    [debtsQuery.data],
  )

  const submitCreate = async (event: FormEvent) => {
    event.preventDefault()
    const numericAmount = Number(amount)
    if (!numericAmount || numericAmount <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await createMutation.mutateAsync({
      amount: numericAmount,
      currency: settings?.default_currency || 'UZS',
      description: description.trim() || undefined,
      source_name: sourceName.trim() || undefined,
      source_contact: sourceContact.trim() || undefined,
      reference: reference.trim() || undefined,
      note: note.trim() || undefined,
    })
  }

  const submitPay = async (debtId: string) => {
    const numericAmount = Number(payAmounts[debtId])
    if (!numericAmount || numericAmount <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await payMutation.mutateAsync({ debtId, amountValue: numericAmount })
  }

  if (debtsQuery.isLoading && !debtsQuery.data) {
    return <LoadingState label={t('loading', language)} />
  }

  return (
    <Page title={t('debts', language)} subtitle={settings?.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('createDebt', language)} />
        <form className="space-y-3" onSubmit={submitCreate}>
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <input className="field" placeholder={t('description', language)} value={description} onChange={(e) => setDescription(e.target.value)} />
          <input className="field" placeholder={t('sourceName', language)} value={sourceName} onChange={(e) => setSourceName(e.target.value)} />
          <input className="field" placeholder={t('sourceContact', language)} value={sourceContact} onChange={(e) => setSourceContact(e.target.value)} />
          <input className="field" placeholder={t('reference', language)} value={reference} onChange={(e) => setReference(e.target.value)} />
          <textarea className="field min-h-[88px]" placeholder={t('note', language)} value={note} onChange={(e) => setNote(e.target.value)} />
          <button type="submit" className="primary-button w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? t('loading', language) : t('save', language)}
          </button>
        </form>
      </Card>

      <Card>
        <SectionTitle title={t('debtList', language)} />
        {debtsQuery.data?.length ? (
          <div className="space-y-3">
            {debtsQuery.data.map((debt) => (
              <div key={debt.id} className="surface-card-muted px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{debt.description || debt.source_name || debt.id.slice(0, 8)}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">{formatDateTime(debt.created_at, language)}</p>
                    {debt.source_name ? <p className="mt-2 text-sm text-[var(--text-soft)]">{t('sourceName', language)}: {debt.source_name}</p> : null}
                    {debt.source_contact ? <p className="mt-1 text-sm text-[var(--text-soft)]">{t('sourceContact', language)}: {debt.source_contact}</p> : null}
                    {debt.note ? <p className="mt-1 text-sm text-[var(--text-soft)]">{debt.note}</p> : null}
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      {t('availableToSpend', language)}: {formatMoney(debt.available_to_spend || 0, debt.currency, locale)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(debt.amount, debt.currency, locale)}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">
                      {t('remaining', language)}: {formatMoney(debt.remaining, debt.currency, locale)}
                    </p>
                    {debt.status ? <p className="mt-1 text-xs text-[var(--text-muted)]">{debt.status}</p> : null}
                  </div>
                </div>
                {debt.remaining > 0 ? (
                  <div className="mt-3 flex gap-2">
                    <input
                      className="field"
                      inputMode="decimal"
                      placeholder={t('amount', language)}
                      value={payAmounts[debt.id] || ''}
                      onChange={(e) => setPayAmounts((current) => ({ ...current, [debt.id]: e.target.value }))}
                    />
                    <button type="button" className="primary-button min-w-[108px]" onClick={() => void submitPay(debt.id)}>
                      {t('pay', language)}
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={t('noDebts', language)} />
        )}
      </Card>

      {openDebts.length ? (
        <Card>
          <SectionTitle title={t('openStatistics', language)} hint={settings?.default_currency || 'UZS'} />
          <div className="space-y-2">
            {openDebts.map((debt) => (
              <div key={debt.id} className="flex items-center justify-between rounded-2xl border border-[var(--border)] px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">{debt.description || debt.source_name || debt.id.slice(0, 8)}</p>
                  <p className="mt-1 text-xs text-[var(--text-soft)]">
                    {t('remaining', language)}: {formatMoney(debt.remaining, debt.currency, locale)}
                  </p>
                </div>
                <div className="text-right text-xs text-[var(--text-muted)]">
                  <p>{t('availableToSpend', language)}</p>
                  <p className="mt-1 font-semibold text-[var(--text)]">{formatMoney(debt.available_to_spend || 0, debt.currency, locale)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </Page>
  )
}

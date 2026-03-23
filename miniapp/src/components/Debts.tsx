import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createDebt, listDebts, payDebt } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatDateTime, formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

type DebtKind = 'cash_loan' | 'credit_purchase'

const debtKindLabel = (kind: DebtKind, lang: 'uz' | 'ru' | 'en') =>
  kind === 'cash_loan' ? t('cashLoan', lang) : t('creditPurchase', lang)

export default function Debts() {
  const queryClient = useQueryClient()
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [kind, setKind] = useState<DebtKind>('cash_loan')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [sourceName, setSourceName] = useState('')
  const [sourceContact, setSourceContact] = useState('')
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
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
      ])
      setAmount('')
      setDescription('')
      setSourceName('')
      setSourceContact('')
      setKind('cash_loan')
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
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
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

  const sortedDebts = useMemo(
    () =>
      [...(debtsQuery.data || [])].sort((left, right) => {
        if (left.kind === right.kind) {
          return new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
        }
        return left.kind === 'cash_loan' ? -1 : 1
      }),
    [debtsQuery.data],
  )

  const cashLoans = sortedDebts.filter((debt) => debt.kind === 'cash_loan')
  const creditPurchases = sortedDebts.filter((debt) => debt.kind === 'credit_purchase')

  const submitCreate = async (event: FormEvent) => {
    event.preventDefault()
    const numericAmount = Number(amount)
    if (!numericAmount || numericAmount <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await createMutation.mutateAsync({
      amount: numericAmount,
      kind,
      currency: settings?.default_currency || 'UZS',
      description: description.trim() || undefined,
      source_name: sourceName.trim() || undefined,
      source_contact: sourceContact.trim() || undefined,
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

  const renderDebtCard = (debt: (typeof sortedDebts)[number]) => (
    <div key={debt.id} className="surface-card-muted px-4 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-[var(--text)]">{debt.description || debt.source_name || debt.id.slice(0, 8)}</p>
            <span className="rounded-full border border-[var(--border)] px-2 py-1 text-[11px] font-medium text-[var(--text-soft)]">
              {debtKindLabel(debt.kind, language)}
            </span>
          </div>
          <p className="mt-1 text-xs text-[var(--text-soft)]">{formatDateTime(debt.created_at, language)}</p>
          {debt.source_name ? <p className="mt-2 text-sm text-[var(--text-soft)]">{t('sourceName', language)}: {debt.source_name}</p> : null}
          {debt.source_contact ? <p className="mt-1 text-sm text-[var(--text-soft)]">{t('sourceContact', language)}: {debt.source_contact}</p> : null}
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            {debt.kind === 'cash_loan'
              ? `${t('availableToSpend', language)}: ${formatMoney(debt.available_to_spend || 0, debt.currency, locale)}`
              : t('creditPurchaseHint', language)}
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
  )

  return (
    <Page title={t('debts', language)} subtitle={settings?.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('createDebt', language)} hint={t('debtType', language)} />
        <div className="mb-3 grid grid-cols-2 gap-2">
          <button type="button" className={`pill-button ${kind === 'cash_loan' ? 'active' : ''}`} onClick={() => setKind('cash_loan')}>
            {t('cashLoan', language)}
          </button>
          <button type="button" className={`pill-button ${kind === 'credit_purchase' ? 'active' : ''}`} onClick={() => setKind('credit_purchase')}>
            {t('creditPurchase', language)}
          </button>
        </div>
        <div className="mb-3 rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
          {kind === 'cash_loan' ? t('cashLoanHint', language) : t('creditPurchaseHint', language)}
        </div>
        <form className="space-y-3" onSubmit={submitCreate}>
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <input className="field" placeholder={t('description', language)} value={description} onChange={(e) => setDescription(e.target.value)} />
          <input className="field" placeholder={t('sourceName', language)} value={sourceName} onChange={(e) => setSourceName(e.target.value)} />
          <input className="field" placeholder={t('sourceContact', language)} value={sourceContact} onChange={(e) => setSourceContact(e.target.value)} />
          <button type="submit" className="primary-button w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? t('loading', language) : t('save', language)}
          </button>
        </form>
      </Card>

      <Card>
        <SectionTitle title={t('cashLoan', language)} />
        {debtsQuery.isError ? (
          <EmptyState title={t('notLoaded', language)} hint={t('retry', language)} />
        ) : cashLoans.length ? (
          <div className="space-y-3">{cashLoans.map(renderDebtCard)}</div>
        ) : (
          <EmptyState title={t('noDebts', language)} hint={t('cashLoanHint', language)} />
        )}
      </Card>

      <Card>
        <SectionTitle title={t('creditPurchase', language)} />
        {debtsQuery.isError ? (
          <EmptyState title={t('notLoaded', language)} hint={t('retry', language)} />
        ) : creditPurchases.length ? (
          <div className="space-y-3">{creditPurchases.map(renderDebtCard)}</div>
        ) : (
          <EmptyState title={t('noDebtSources', language)} hint={t('creditPurchaseHint', language)} />
        )}
      </Card>
    </Page>
  )
}

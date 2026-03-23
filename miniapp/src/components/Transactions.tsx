import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createTransaction, deleteTransaction, getBalance, getCategories, getTransactions, listDebts } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatDateTime, formatMoney } from '@/lib/format'
import { getTransactionDisplayTitle, shouldShowTransactionDescription } from '@/lib/transactionDisplay'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

type EntryType = 'income' | 'expense'

const transactionTitle = (
  transaction: {
    type: string
    debt_kind?: 'cash_loan' | 'credit_purchase' | null
    description?: string
    category?: { icon?: string; name?: string }
  },
  language: 'uz' | 'ru' | 'en',
) => {
  const fallbackTitle =
    transaction.type === 'debt'
      ? transaction.debt_kind === 'cash_loan'
        ? t('cashLoan', language)
        : t('creditPurchase', language)
      : transaction.type === 'debt_payment'
        ? t('pay', language)
        : transaction.type

  return getTransactionDisplayTitle(transaction, fallbackTitle)
}

const transactionPrefix = (transaction: { type: string; debt_kind?: 'cash_loan' | 'credit_purchase' | null }) => {
  if (transaction.type === 'expense' || transaction.type === 'transfer_out' || transaction.type === 'debt_payment') {
    return '-'
  }
  if (transaction.type === 'debt') {
    return transaction.debt_kind === 'cash_loan' ? '+' : '-'
  }
  return '+'
}

export default function Transactions() {
  const queryClient = useQueryClient()
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [type, setType] = useState<EntryType>('expense')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState<number | ''>('')
  const [fundingSource, setFundingSource] = useState<'main' | 'debt'>('main')
  const [debtId, setDebtId] = useState<string>('')
  const [filter, setFilter] = useState<'all' | 'income' | 'expense'>('all')

  const transactionsQuery = useQuery({
    queryKey: ['transactions', filter],
    queryFn: () => getTransactions({ limit: 40, type: filter === 'all' ? undefined : filter }),
  })
  const categoriesQuery = useQuery({
    queryKey: ['categories', type],
    queryFn: () => getCategories(type),
  })
  const balanceQuery = useQuery({
    queryKey: ['balance'],
    queryFn: getBalance,
  })
  const debtsQuery = useQuery({
    queryKey: ['debts-for-expense'],
    queryFn: listDebts,
  })

  const createMutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['balance'] }),
        queryClient.invalidateQueries({ queryKey: ['debts-for-expense'] }),
        queryClient.invalidateQueries({ queryKey: ['debts'] }),
      ])
      setAmount('')
      setDescription('')
      setCategoryId('')
      setDebtId('')
      setFundingSource('main')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: async (error: any) => {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTransaction,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['balance'] }),
      ])
    },
  })

  const openDebts = useMemo(
    () =>
      (debtsQuery.data || []).filter(
        (debt) =>
          debt.kind === 'cash_loan' &&
          (debt.available_to_spend || 0) > 0 &&
          (debt.status === 'active' || debt.status === 'partially_repaid' || !debt.status),
      ),
    [debtsQuery.data],
  )

  const numericAmount = Number(amount || 0)
  const mainBalance = balanceQuery.data?.total_balance || 0
  const insufficientMain = type === 'expense' && fundingSource === 'main' && numericAmount > mainBalance
  const requiresDebtChoice = type === 'expense' && fundingSource === 'debt'

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const numericAmount = Number(amount)
    if (!numericAmount || numericAmount <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    if (type === 'expense' && insufficientMain) {
      await showAlert(t('debtFallbackHint', language))
      return
    }
    if (requiresDebtChoice && !debtId) {
      await showAlert(openDebts.length ? t('selectDebt', language) : t('createDebtFirst', language))
      return
    }
    await createMutation.mutateAsync({
      type,
      amount: numericAmount,
      currency: settings?.default_currency || 'UZS',
      category_id: categoryId || undefined,
      description: description.trim() || undefined,
      funding_source: type === 'expense' ? fundingSource : undefined,
      debt_id: requiresDebtChoice ? debtId || undefined : undefined,
    })
  }

  if (transactionsQuery.isLoading && !transactionsQuery.data) {
    return <LoadingState label={t('loading', language)} />
  }

  return (
    <Page title={t('activity', language)} subtitle={`${settings?.active_group_name || '-'} - ${settings?.default_currency || 'UZS'}`}>
      <Card>
        <SectionTitle title={`${t('addIncome', language)} / ${t('addExpense', language)}`} />
        <div className="mb-3 flex gap-2">
          <button type="button" onClick={() => setType('income')} className={`pill-button ${type === 'income' ? 'active' : ''}`}>
            {t('income', language)}
          </button>
          <button type="button" onClick={() => setType('expense')} className={`pill-button ${type === 'expense' ? 'active' : ''}`}>
            {t('expense', language)}
          </button>
        </div>

        <form className="space-y-3" onSubmit={submit}>
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <select className="field" value={categoryId} onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}>
            <option value="">{t('description', language)} / category</option>
            {(categoriesQuery.data || []).map((category) => (
              <option key={category.id} value={category.id}>
                {category.icon} {category.name}
              </option>
            ))}
          </select>
          {type === 'expense' ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <button type="button" className={`pill-button ${fundingSource === 'main' ? 'active' : ''}`} onClick={() => setFundingSource('main')}>
                  {t('mainSource', language)}
                </button>
                <button type="button" className={`pill-button ${fundingSource === 'debt' ? 'active' : ''}`} onClick={() => setFundingSource('debt')}>
                  {t('debtSource', language)}
                </button>
              </div>
              {insufficientMain ? (
                <div className="rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
                  {t('debtFallbackHint', language)}
                </div>
              ) : null}
              {fundingSource === 'debt' ? (
                <>
                  {debtsQuery.isError ? (
                    <div className="rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
                      {t('notLoaded', language)}. {t('retry', language)}.
                    </div>
                  ) : openDebts.length ? (
                    <select className="field" value={debtId} onChange={(e) => setDebtId(e.target.value)}>
                      <option value="">{t('selectDebt', language)}</option>
                      {openDebts.map((debt) => (
                        <option key={debt.id} value={debt.id}>
                          {(debt.description || debt.source_name || debt.id).slice(0, 42)} - {formatMoney(debt.available_to_spend || 0, debt.currency, locale)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
                      {t('noDebtSources', language)}. {t('createDebtFirst', language)}.
                    </div>
                  )}
                </>
              ) : null}
            </>
          ) : null}
          <textarea className="field min-h-[94px]" placeholder={t('description', language)} value={description} onChange={(e) => setDescription(e.target.value)} />
          <button type="submit" className="primary-button w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? t('loading', language) : t('save', language)}
          </button>
        </form>
      </Card>

      <Card>
        <SectionTitle title={t('recentOperations', language)} />
        <div className="mb-3 flex flex-wrap gap-2">
          <button type="button" onClick={() => setFilter('all')} className={`pill-button ${filter === 'all' ? 'active' : ''}`}>All</button>
          <button type="button" onClick={() => setFilter('income')} className={`pill-button ${filter === 'income' ? 'active' : ''}`}>{t('income', language)}</button>
          <button type="button" onClick={() => setFilter('expense')} className={`pill-button ${filter === 'expense' ? 'active' : ''}`}>{t('expense', language)}</button>
        </div>
        {transactionsQuery.data?.length ? (
          <div className="space-y-3">
            {transactionsQuery.data.map((transaction) => {
              const title = transactionTitle(transaction, language)

              return (
                <div key={transaction.id} className="surface-card-muted px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">{title}</p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">{formatDateTime(transaction.transaction_date, language)}</p>
                      {shouldShowTransactionDescription(transaction, title) ? <p className="mt-2 text-sm text-[var(--text-soft)]">{transaction.description}</p> : null}
                      {transaction.type === 'debt' ? (
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {transaction.debt_kind === 'cash_loan' ? t('cashLoanHint', language) : t('creditPurchaseHint', language)}
                        </p>
                      ) : null}
                      {transaction.funding_source ? (
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {transaction.funding_source === 'debt' && transaction.main_used_amount
                            ? t('mainAndDebtSource', language)
                            : transaction.funding_source === 'debt'
                              ? t('debtSource', language)
                              : t('mainSource', language)}
                        </p>
                      ) : null}
                      {transaction.debt_source_name ? (
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {t('sourceName', language)}: {transaction.debt_source_name}
                        </p>
                      ) : null}
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-[var(--text)]">
                        {transactionPrefix(transaction)}
                        {formatMoney(transaction.amount, transaction.currency, locale)}
                      </p>
                      {(transaction.type === 'income' || transaction.type === 'expense') ? (
                        <button
                          type="button"
                          className="mt-2 text-xs text-[var(--danger)]"
                          onClick={() => deleteMutation.mutate(transaction.id)}
                        >
                          Delete
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState title={t('noOperations', language)} />
        )}
      </Card>
    </Page>
  )
}

import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getBalance, getTransactions } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { t } from '@/i18n'
import { formatDateTime, formatMoney } from '@/lib/format'
import { getTransactionDisplayTitle, shouldShowTransactionDescription } from '@/lib/transactionDisplay'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

const transactionTypeLabel = (type: string, lang: 'uz' | 'ru' | 'en') => {
  if (type === 'income') return t('income', lang)
  if (type === 'expense') return t('expense', lang)
  if (type === 'transfer_out') return `${t('transfers', lang)} out`
  if (type === 'transfer_in') return `${t('transfers', lang)} in`
  if (type === 'debt_payment') return t('pay', lang)
  return type
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

export default function Dashboard() {
  const { language, locale, settings } = useAppSettings()
  const balanceQuery = useQuery({ queryKey: ['balance'], queryFn: getBalance })
  const transactionsQuery = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => getTransactions({ limit: 5 }),
  })

  if (balanceQuery.isLoading) {
    return <LoadingState label={t('loading', language)} />
  }

  if (!balanceQuery.data) {
    return <EmptyState title={t('notLoaded', language)} hint={t('retry', language)} />
  }

  const balance = balanceQuery.data
  const recentTransactions = transactionsQuery.data || []

  return (
    <Page
      title={settings?.active_group_name || t('home', language)}
      subtitle={`${t('currentGroup', language)} - ${balance.group_name || settings?.active_group_name || '-'}`}
    >
      <Card>
        <SectionTitle title={t('totalBalance', language)} hint={balance.currency} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('totalBalance', language)}</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text)]">
              {formatMoney(balance.total_balance, balance.currency, locale)}
            </p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('debtBalance', language)}</p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text)]">
              {formatMoney(balance.debt_balance, balance.currency, locale)}
            </p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('ownBalance', language)}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">
              {formatMoney(balance.own_balance, balance.currency, locale)}
            </p>
          </div>
          <div className="surface-card-muted px-4 py-4">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('receivedBalance', language)}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">
              {formatMoney(balance.received_balance, balance.currency, locale)}
            </p>
          </div>
        </div>
        <div className="mt-3 rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
          {t('outstandingDebt', language)}: <span className="font-semibold text-[var(--text)]">{formatMoney(balance.outstanding_debt_balance, balance.currency, locale)}</span>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('quickActions', language)} />
        <div className="grid grid-cols-1 gap-3">
          <Link to="/transactions" className="surface-card-muted px-4 py-4">
            <p className="text-sm font-semibold text-[var(--text)]">{t('addIncome', language)} / {t('addExpense', language)}</p>
            <p className="mt-1 text-sm text-[var(--text-soft)]">{t('activity', language)}</p>
          </Link>
          <Link to="/transfers" className="surface-card-muted px-4 py-4">
            <p className="text-sm font-semibold text-[var(--text)]">{t('createTransfer', language)}</p>
            <p className="mt-1 text-sm text-[var(--text-soft)]">{t('transfers', language)}</p>
          </Link>
          <Link to="/debts" className="surface-card-muted px-4 py-4">
            <p className="text-sm font-semibold text-[var(--text)]">{t('manageDebts', language)}</p>
            <p className="mt-1 text-sm text-[var(--text-soft)]">{t('debtBalance', language)}</p>
          </Link>
          {settings?.is_group_admin || settings?.is_admin ? (
            <Link to="/team" className="surface-card-muted px-4 py-4">
              <p className="text-sm font-semibold text-[var(--text)]">{t('manageWorkers', language)}</p>
              <p className="mt-1 text-sm text-[var(--text-soft)]">{t('workers', language)}</p>
            </Link>
          ) : null}
          <div className="grid grid-cols-2 gap-3">
            <Link to="/statistics" className="surface-card-muted px-4 py-4">
              <p className="text-sm font-semibold text-[var(--text)]">{t('statistics', language)}</p>
              <p className="mt-1 text-sm text-[var(--text-soft)]">{t('openStatistics', language)}</p>
            </Link>
            <Link to="/settings" className="surface-card-muted px-4 py-4">
              <p className="text-sm font-semibold text-[var(--text)]">{t('settings', language)}</p>
              <p className="mt-1 text-sm text-[var(--text-soft)]">{t('language', language)} - {t('theme', language)}</p>
            </Link>
          </div>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('recentOperations', language)} />
        {recentTransactions.length ? (
          <div className="space-y-3">
            {recentTransactions.map((transaction) => {
              const fallbackTitle =
                transaction.type === 'debt'
                  ? transaction.debt_kind === 'cash_loan'
                    ? t('cashLoan', language)
                    : t('creditPurchase', language)
                  : transactionTypeLabel(transaction.type, language)
              const title = getTransactionDisplayTitle(transaction, fallbackTitle)

              return (
                <div key={transaction.id} className="surface-card-muted px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">{title}</p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">
                        {formatDateTime(transaction.transaction_date, language)}
                      </p>
                      {shouldShowTransactionDescription(transaction, title) ? (
                        <p className="mt-2 text-sm text-[var(--text-soft)]">{transaction.description}</p>
                      ) : null}
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-[var(--text)]">
                        {transactionPrefix(transaction)}
                        {formatMoney(transaction.amount, transaction.currency, locale)}
                      </p>
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


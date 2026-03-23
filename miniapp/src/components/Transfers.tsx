import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createTransfer,
  getSentTransferGroupDetails,
  getSentTransferGroups,
  getTransferRecipients,
  getTransfers,
} from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatDateTime, formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

export default function Transfers() {
  const queryClient = useQueryClient()
  const { language, locale, settings } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [recipientSearch, setRecipientSearch] = useState('')
  const [recipientId, setRecipientId] = useState<number | ''>('')
  const [recipientLabel, setRecipientLabel] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [tab, setTab] = useState<'sent' | 'received'>('sent')
  const [selectedRecipientGroup, setSelectedRecipientGroup] = useState<number | null>(null)

  const recipientsQuery = useQuery({
    queryKey: ['transfer-recipients', recipientSearch],
    queryFn: () => getTransferRecipients({ search: recipientSearch || undefined, limit: 20 }),
  })
  const sentGroupsQuery = useQuery({
    queryKey: ['sent-transfer-groups'],
    queryFn: () => getSentTransferGroups(),
  })
  const receivedQuery = useQuery({
    queryKey: ['received-transfers'],
    queryFn: () => getTransfers('received'),
  })
  const selectedGroupQuery = useQuery({
    queryKey: ['sent-transfer-group-detail', selectedRecipientGroup],
    queryFn: () => getSentTransferGroupDetails(selectedRecipientGroup as number),
    enabled: selectedRecipientGroup !== null,
  })

  const createMutation = useMutation({
    mutationFn: createTransfer,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['sent-transfer-groups'] }),
        queryClient.invalidateQueries({ queryKey: ['received-transfers'] }),
        queryClient.invalidateQueries({ queryKey: ['balance'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
      ])
      setRecipientId('')
      setRecipientLabel('')
      setAmount('')
      setDescription('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: async (error: any) => {
      haptic.error()
      await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
    },
  })

  const recipientOptions = useMemo(() => recipientsQuery.data || [], [recipientsQuery.data])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!recipientId) {
      await showAlert(t('chooseRecipient', language))
      return
    }
    const numericAmount = Number(amount)
    if (!numericAmount || numericAmount <= 0) {
      await showAlert(t('requestFailed', language))
      return
    }
    await createMutation.mutateAsync({
      recipient_telegram_id: Number(recipientId),
      amount: numericAmount,
      currency: settings?.default_currency || 'UZS',
      description: description.trim() || undefined,
    })
  }

  if ((sentGroupsQuery.isLoading && !sentGroupsQuery.data) || (receivedQuery.isLoading && !receivedQuery.data)) {
    return <LoadingState label={t('loading', language)} />
  }

  return (
    <Page title={t('transfers', language)} subtitle={settings?.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('createTransfer', language)} />
        <form className="space-y-3" onSubmit={submit}>
          <input
            className="field"
            placeholder={t('recipient', language)}
            value={recipientSearch}
            onChange={(e) => setRecipientSearch(e.target.value)}
          />
          <div className="surface-card-muted max-h-[220px] overflow-auto px-3 py-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-muted)]">
              {t('chooseRecipient', language)}
            </p>
            {recipientOptions.length ? (
              <div className="space-y-2">
                {recipientOptions.map((recipient) => {
                  const active = recipientId === recipient.id
                  return (
                    <button
                      key={recipient.id}
                      type="button"
                      onClick={() => {
                        setRecipientId(recipient.id)
                        setRecipientLabel(recipient.display_name)
                      }}
                      className="flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left"
                      style={{
                        borderColor: active ? 'var(--accent)' : 'var(--border)',
                        background: active ? 'var(--surface-strong)' : 'transparent',
                      }}
                    >
                      <div>
                        <p className="text-sm font-semibold text-[var(--text)]">{recipient.display_name}</p>
                        <p className="mt-1 text-xs text-[var(--text-soft)]">
                          {recipient.first_name} {recipient.last_name || ''}
                        </p>
                      </div>
                      <span className="text-xs text-[var(--text-muted)]">ID {recipient.id}</span>
                    </button>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-soft)]">{t('noRecipients', language)}</p>
            )}
          </div>
          {recipientLabel ? (
            <div className="rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
              {t('recipient', language)}: <span className="font-semibold text-[var(--text)]">{recipientLabel}</span>
            </div>
          ) : null}
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={amount} onChange={(e) => setAmount(e.target.value)} />
          <textarea className="field min-h-[84px]" placeholder={t('comment', language)} value={description} onChange={(e) => setDescription(e.target.value)} />
          <button type="submit" className="primary-button w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? t('loading', language) : t('send', language)}
          </button>
        </form>
      </Card>

      <Card>
        <SectionTitle title={t('transfers', language)} />
        <div className="mb-3 flex gap-2">
          <button type="button" onClick={() => setTab('sent')} className={`pill-button ${tab === 'sent' ? 'active' : ''}`}>
            {t('sent', language)}
          </button>
          <button type="button" onClick={() => setTab('received')} className={`pill-button ${tab === 'received' ? 'active' : ''}`}>
            {t('received', language)}
          </button>
        </div>

        {tab === 'sent' ? (
          sentGroupsQuery.data?.length ? (
            <div className="space-y-3">
              {sentGroupsQuery.data.map((group) => (
                <button
                  key={group.recipient_id}
                  type="button"
                  onClick={() => setSelectedRecipientGroup(group.recipient_id)}
                  className="surface-card-muted block w-full px-4 py-4 text-left"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">{group.recipient_name}</p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">
                        {group.transfer_count} transfer · {formatDateTime(group.last_transfer_at, language)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(group.amount, group.currency, locale)}</p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">
                        {t('remaining', language)}: {formatMoney(group.remaining_amount, group.currency, locale)}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title={t('noOperations', language)} />
          )
        ) : receivedQuery.data?.length ? (
          <div className="space-y-3">
            {receivedQuery.data.map((transfer) => (
              <div key={transfer.id} className="surface-card-muted px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{transfer.recipient_name || transfer.recipient_username || `#${transfer.recipient_id}`}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">{formatDateTime(transfer.created_at, language)}</p>
                    {transfer.description ? <p className="mt-2 text-sm text-[var(--text-soft)]">{transfer.description}</p> : null}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(transfer.amount, transfer.currency, locale)}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">
                      {t('remaining', language)}: {formatMoney(transfer.remaining_amount, transfer.currency, locale)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={t('noOperations', language)} />
        )}
      </Card>

      {selectedGroupQuery.data ? (
        <Card>
          <SectionTitle title={selectedGroupQuery.data.recipient_name} hint={t('recentOperations', language)} />
          <div className="space-y-3">
            {selectedGroupQuery.data.transfers.map((transfer) => (
              <div key={transfer.id} className="surface-card-muted px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{formatDateTime(transfer.created_at, language)}</p>
                    {transfer.description ? <p className="mt-1 text-sm text-[var(--text-soft)]">{transfer.description}</p> : null}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(transfer.amount, transfer.currency, locale)}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">
                      {t('remaining', language)}: {formatMoney(transfer.remaining_amount, transfer.currency, locale)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {selectedGroupQuery.data.expenses.length ? (
              <>
                <SectionTitle title={t('expense', language)} />
                {selectedGroupQuery.data.expenses.map((expense) => (
                  <div key={expense.id} className="surface-card-muted px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[var(--text)]">{expense.category.icon} {expense.category.name}</p>
                        <p className="mt-1 text-xs text-[var(--text-soft)]">{formatDateTime(expense.created_at, language)}</p>
                        {expense.description ? <p className="mt-2 text-sm text-[var(--text-soft)]">{expense.description}</p> : null}
                      </div>
                      <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(expense.amount, expense.currency, locale)}</p>
                    </div>
                  </div>
                ))}
              </>
            ) : null}
          </div>
        </Card>
      ) : null}
    </Page>
  )
}

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createGroup,
  createWorker,
  getGroupMembers,
  getGroupUserOverview,
  getGroups,
  getWorkersSummary,
  renameGroup,
  upsertGroupMember,
} from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { formatMoney } from '@/lib/format'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState, LoadingState } from '@/components/shared/States'

const currentMonthRange = () => {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  return { start, end }
}

export const AdminPanel = () => {
  const queryClient = useQueryClient()
  const { settings, language, locale } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [groupName, setGroupName] = useState('')
  const [renameValue, setRenameValue] = useState('')
  const [memberId, setMemberId] = useState('')
  const [memberRole, setMemberRole] = useState<'admin' | 'member'>('member')
  const [workerName, setWorkerName] = useState('')
  const [workerRate, setWorkerRate] = useState('')

  const month = useMemo(currentMonthRange, [])
  const canManageAdmin = Boolean(settings?.is_group_admin || settings?.is_admin)

  const groupsQuery = useQuery({
    queryKey: ['admin-groups'],
    queryFn: getGroups,
    enabled: canManageAdmin,
  })

  const membersQuery = useQuery({
    queryKey: ['admin-members', settings?.active_group_id],
    queryFn: () => getGroupMembers(settings?.active_group_id as number),
    enabled: Boolean(settings?.active_group_id && canManageAdmin),
  })

  const workersSummaryQuery = useQuery({
    queryKey: ['admin-workers-summary', settings?.active_group_id, month.start, month.end],
    queryFn: () => getWorkersSummary({ start_date: month.start, end_date: month.end }),
    enabled: Boolean(settings?.active_group_id && canManageAdmin),
  })
  const overviewQuery = useQuery({
    queryKey: ['group-user-overview', settings?.active_group_id],
    queryFn: () => getGroupUserOverview(settings?.active_group_id as number),
    enabled: Boolean(settings?.active_group_id && canManageAdmin),
  })

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-groups'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-members'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-workers-summary'] }),
      queryClient.invalidateQueries({ queryKey: ['group-user-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['user-settings'] }),
      queryClient.invalidateQueries({ queryKey: ['workers'] }),
      queryClient.invalidateQueries({ queryKey: ['group-members'] }),
    ])
  }

  const handleError = async (error: any) => {
    haptic.error()
    await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
  }

  const createGroupMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: async () => {
      await refresh()
      setGroupName('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const renameGroupMutation = useMutation({
    mutationFn: ({ groupId, name }: { groupId: number; name: string }) => renameGroup(groupId, name),
    onSuccess: async () => {
      await refresh()
      setRenameValue('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const addMemberMutation = useMutation({
    mutationFn: ({ groupId, userId, role }: { groupId: number; userId: number; role: 'admin' | 'member' }) =>
      upsertGroupMember(groupId, userId, role),
    onSuccess: async () => {
      await refresh()
      setMemberId('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const createWorkerMutation = useMutation({
    mutationFn: ({ full_name, rate }: { full_name: string; rate: number }) =>
      createWorker({
        full_name,
        payment_type: 'daily',
        rate,
        currency: (settings?.default_currency || 'UZS') as 'UZS' | 'USD',
        start_date: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: async () => {
      await refresh()
      setWorkerName('')
      setWorkerRate('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  if (!canManageAdmin) {
    return (
      <Page title={t('admin', language)} subtitle={settings?.active_group_name || '-'}>
        <EmptyState title={t('notAllowed', language)} />
      </Page>
    )
  }

  if (groupsQuery.isLoading && !groupsQuery.data) {
    return <LoadingState label={t('loading', language)} />
  }

  const currentGroup = groupsQuery.data?.find((group) => group.id === settings?.active_group_id)

  return (
    <Page title={t('admin', language)} subtitle={settings?.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('createNewGroup', language)} />
        <div className="space-y-3">
          <input className="field" placeholder={t('groupName', language)} value={groupName} onChange={(e) => setGroupName(e.target.value)} />
          <button type="button" className="primary-button w-full" onClick={() => createGroupMutation.mutate(groupName)} disabled={createGroupMutation.isPending}>
            {t('save', language)}
          </button>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('currentGroup', language)} />
        {groupsQuery.data?.length ? (
          <div className="space-y-3">
            {groupsQuery.data.map((group) => (
              <div key={group.id} className="surface-card-muted px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{group.name}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">{group.role}</p>
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">#{group.id}</span>
                </div>
              </div>
            ))}
            {currentGroup ? (
              <>
                <input className="field" placeholder={t('rename', language)} value={renameValue} onChange={(e) => setRenameValue(e.target.value)} />
                <button
                  type="button"
                  className="secondary-button w-full"
                  onClick={() => renameGroupMutation.mutate({ groupId: currentGroup.id, name: renameValue || currentGroup.name })}
                  disabled={renameGroupMutation.isPending}
                >
                  {t('rename', language)}
                </button>
              </>
            ) : null}
          </div>
        ) : (
          <EmptyState title={t('noGroups', language)} />
        )}
      </Card>

      <Card>
        <SectionTitle title={t('usersOverview', language)} hint={t('members', language)} />
        {overviewQuery.data?.length ? (
          <div className="space-y-3">
            {overviewQuery.data.map((item) => (
              <div key={item.user_id} className="surface-card-muted px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{item.display_name}</p>
                    <p className="mt-1 text-xs text-[var(--text-soft)]">
                      @{item.username || 'no_username'} - {item.role}
                    </p>
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">ID {item.user_id}</span>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <div className="rounded-2xl border border-[var(--border)] px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('totalBalance', language)}</p>
                    <p className="mt-2 text-sm font-semibold text-[var(--text)]">{formatMoney(item.total_balance, settings?.default_currency || 'UZS', locale)}</p>
                  </div>
                  <div className="rounded-2xl border border-[var(--border)] px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('debtBalance', language)}</p>
                    <p className="mt-2 text-sm font-semibold text-[var(--text)]">{formatMoney(item.debt_balance, settings?.default_currency || 'UZS', locale)}</p>
                  </div>
                  <div className="rounded-2xl border border-[var(--border)] px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">{t('outstandingDebt', language)}</p>
                    <p className="mt-2 text-sm font-semibold text-[var(--text)]">{formatMoney(item.outstanding_debt_balance, settings?.default_currency || 'UZS', locale)}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--text-soft)]">
                  <span>{t('debts', language)}: {item.debt_count}</span>
                  <span>{t('activeDebts', language)}: {item.active_debt_count}</span>
                </div>
                {item.recent_transactions.length ? (
                  <div className="mt-3 space-y-2">
                    {item.recent_transactions.map((transaction) => (
                      <div key={transaction.id} className="rounded-2xl border border-[var(--border)] px-3 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-[var(--text)]">{transaction.description}</p>
                            <p className="mt-1 text-xs text-[var(--text-soft)]">{transaction.type}</p>
                          </div>
                          <p className="text-sm font-semibold text-[var(--text)]">
                            {formatMoney(transaction.amount, transaction.currency, locale)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={t('members', language)} />
        )}
      </Card>

      <Card>
        <SectionTitle title={t('members', language)} />
        <div className="space-y-3">
          <input className="field" placeholder={t('userId', language)} value={memberId} onChange={(e) => setMemberId(e.target.value)} />
          <select className="field" value={memberRole} onChange={(e) => setMemberRole(e.target.value as 'admin' | 'member')}>
            <option value="member">{t('member', language)}</option>
            <option value="admin">{t('groupAdmin', language)}</option>
          </select>
          <button
            type="button"
            className="primary-button w-full"
            onClick={() => settings?.active_group_id && addMemberMutation.mutate({ groupId: settings.active_group_id, userId: Number(memberId), role: memberRole })}
            disabled={addMemberMutation.isPending}
          >
            {t('addMember', language)}
          </button>
          {membersQuery.data?.length ? (
            <div className="space-y-2">
              {membersQuery.data.map((member) => (
                <div key={member.user_id} className="surface-card-muted px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">
                        {member.first_name} {member.last_name || ''}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">
                        @{member.username || 'no_username'} - {member.role}
                      </p>
                    </div>
                    <span className="text-xs text-[var(--text-muted)]">ID {member.user_id}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={t('members', language)} />
          )}
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('workers', language)} hint={`${month.start} -> ${month.end}`} />
        <div className="space-y-3">
          <input className="field" placeholder={t('fullName', language)} value={workerName} onChange={(e) => setWorkerName(e.target.value)} />
          <input className="field" inputMode="decimal" placeholder={t('amount', language)} value={workerRate} onChange={(e) => setWorkerRate(e.target.value)} />
          <button
            type="button"
            className="primary-button w-full"
            onClick={() => createWorkerMutation.mutate({ full_name: workerName, rate: Number(workerRate) })}
            disabled={createWorkerMutation.isPending}
          >
            {t('addWorker', language)}
          </button>

          {workersSummaryQuery.data?.workers?.length ? (
            <div className="space-y-2">
              {workersSummaryQuery.data.workers.map((worker) => (
                <div key={worker.worker_id} className="surface-card-muted px-4 py-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">{worker.full_name}</p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">{worker.payment_type}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-[var(--text)]">{formatMoney(worker.payable_amount, worker.currency, locale)}</p>
                      <p className="mt-1 text-xs capitalize text-[var(--text-soft)]">{worker.status}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={t('noWorkers', language)} />
          )}
        </div>
      </Card>
    </Page>
  )
}

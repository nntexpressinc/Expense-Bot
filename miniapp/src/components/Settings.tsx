import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createGroup, getGroupMembers, removeGroupMember, renameGroup, upsertGroupMember } from '@/api/endpoints'
import { useAppSettings } from '@/hooks/useAppSettings'
import { useTelegram } from '@/hooks/useTelegram'
import { t } from '@/i18n'
import { Card, Page, SectionTitle } from '@/components/shared/Page'
import { EmptyState } from '@/components/shared/States'

export default function Settings() {
  const queryClient = useQueryClient()
  const { settings, language, setLanguage, setCurrency, setTheme, setActiveGroup, refreshSettings, isMutating } = useAppSettings()
  const { showAlert, haptic } = useTelegram()
  const [newGroupName, setNewGroupName] = useState('')
  const [renameValue, setRenameValue] = useState('')
  const [memberUserId, setMemberUserId] = useState('')
  const [memberRole, setMemberRole] = useState<'admin' | 'member'>('member')

  const activeGroupId = settings?.active_group_id || undefined

  const membersQuery = useQuery({
    queryKey: ['group-members', activeGroupId],
    queryFn: () => getGroupMembers(activeGroupId as number),
    enabled: Boolean(activeGroupId && (settings?.is_group_admin || settings?.is_admin)),
  })

  const refreshEverything = async () => {
    await Promise.all([
      refreshSettings(),
      queryClient.invalidateQueries({ queryKey: ['group-members'] }),
      queryClient.invalidateQueries({ queryKey: ['balance'] }),
      queryClient.invalidateQueries({ queryKey: ['workers'] }),
      queryClient.invalidateQueries({ queryKey: ['transactions'] }),
      queryClient.invalidateQueries({ queryKey: ['transfers'] }),
      queryClient.invalidateQueries({ queryKey: ['debts'] }),
    ])
  }

  const handleError = async (error: any) => {
    haptic.error()
    await showAlert(error?.response?.data?.detail || error?.message || t('requestFailed', language))
  }

  const createGroupMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: async () => {
      await refreshEverything()
      setNewGroupName('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const renameGroupMutation = useMutation({
    mutationFn: ({ groupId, name }: { groupId: number; name: string }) => renameGroup(groupId, name),
    onSuccess: async () => {
      await refreshEverything()
      setRenameValue('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const memberMutation = useMutation({
    mutationFn: ({ groupId, userId, role }: { groupId: number; userId: number; role: 'admin' | 'member' }) =>
      upsertGroupMember(groupId, userId, role),
    onSuccess: async () => {
      await refreshEverything()
      setMemberUserId('')
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const removeMemberMutation = useMutation({
    mutationFn: ({ groupId, userId }: { groupId: number; userId: number }) => removeGroupMember(groupId, userId),
    onSuccess: async () => {
      await refreshEverything()
      haptic.success()
      await showAlert(t('successSaved', language))
    },
    onError: handleError,
  })

  const currentGroup = useMemo(
    () => settings?.groups.find((group) => group.id === settings.active_group_id),
    [settings],
  )

  if (!settings) {
    return <EmptyState title={t('notLoaded', language)} />
  }

  return (
    <Page title={t('settings', language)} subtitle={settings.active_group_name || '-'}>
      <Card>
        <SectionTitle title={t('language', language)} />
        <div className="grid grid-cols-3 gap-2">
          {(['uz', 'ru', 'en'] as const).map((langItem) => (
            <button
              key={langItem}
              type="button"
              onClick={() => setLanguage(langItem)}
              className={`pill-button ${settings.language_code === langItem ? 'active' : ''}`}
              disabled={isMutating}
            >
              {langItem.toUpperCase()}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('currency', language)} />
        <div className="grid grid-cols-2 gap-2">
          {(['UZS', 'USD'] as const).map((currency) => (
            <button
              key={currency}
              type="button"
              onClick={() => setCurrency(currency)}
              className={`pill-button ${settings.default_currency === currency ? 'active' : ''}`}
              disabled={isMutating}
            >
              {currency}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('theme', language)} />
        <div className="grid grid-cols-2 gap-2">
          <button type="button" className={`pill-button ${settings.theme_preference === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')}>
            {t('lightTheme', language)}
          </button>
          <button type="button" className={`pill-button ${settings.theme_preference === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')}>
            {t('darkTheme', language)}
          </button>
        </div>
      </Card>

      <Card>
        <SectionTitle title={t('currentGroup', language)} />
        {settings.groups.length ? (
          <div className="space-y-3">
            <select
              className="field"
              value={settings.active_group_id || ''}
              onChange={(e) => setActiveGroup(Number(e.target.value))}
            >
              {settings.groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name} · {group.role}
                </option>
              ))}
            </select>
            <div className="rounded-2xl border border-[var(--border)] px-4 py-3 text-sm text-[var(--text-soft)]">
              {t('currentGroup', language)}: <span className="font-semibold text-[var(--text)]">{settings.active_group_name}</span>
            </div>
          </div>
        ) : (
          <EmptyState title={t('noGroups', language)} />
        )}
      </Card>

      {settings.is_group_admin || settings.is_admin ? (
        <>
          <Card>
            <SectionTitle title={t('createNewGroup', language)} />
            <div className="space-y-3">
              <input className="field" placeholder={t('groupName', language)} value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} />
              <button type="button" className="primary-button w-full" onClick={() => createGroupMutation.mutate(newGroupName)}>
                {t('save', language)}
              </button>
            </div>
          </Card>

          {currentGroup ? (
            <Card>
              <SectionTitle title={currentGroup.name} hint={currentGroup.role} />
              <div className="space-y-3">
                <input className="field" placeholder={t('rename', language)} value={renameValue} onChange={(e) => setRenameValue(e.target.value)} />
                <button
                  type="button"
                  className="secondary-button w-full"
                  onClick={() => renameGroupMutation.mutate({ groupId: currentGroup.id, name: renameValue || currentGroup.name })}
                >
                  {t('rename', language)}
                </button>
                <input className="field" placeholder={t('userId', language)} value={memberUserId} onChange={(e) => setMemberUserId(e.target.value)} />
                <select className="field" value={memberRole} onChange={(e) => setMemberRole(e.target.value as 'admin' | 'member')}>
                  <option value="member">{t('member', language)}</option>
                  <option value="admin">{t('groupAdmin', language)}</option>
                </select>
                <button
                  type="button"
                  className="primary-button w-full"
                  onClick={() => memberMutation.mutate({ groupId: currentGroup.id, userId: Number(memberUserId), role: memberRole })}
                >
                  {t('addMember', language)}
                </button>
              </div>
            </Card>
          ) : null}

          <Card>
            <SectionTitle title={t('members', language)} />
            {membersQuery.data?.length ? (
              <div className="space-y-2">
                {membersQuery.data.map((member) => (
                  <div key={member.user_id} className="surface-card-muted flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--text)]">
                        {member.first_name} {member.last_name || ''}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-soft)]">
                        @{member.username || 'no_username'} · {member.role}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="text-xs text-[var(--danger)]"
                      onClick={() => currentGroup && removeMemberMutation.mutate({ groupId: currentGroup.id, userId: member.user_id })}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title={t('members', language)} hint={t('noGroups', language)} />
            )}
          </Card>

          <Card>
            <SectionTitle title={t('admin', language)} />
            <Link to="/admin" className="primary-button block w-full text-center">
              {t('admin', language)}
            </Link>
          </Card>
        </>
      ) : null}
    </Page>
  )
}

import { useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  UserSettings,
  getUserSettings,
  updateActiveGroup,
  updateCurrency,
  updateLanguage,
  updateTheme,
} from '@/api/endpoints'
import { localeFromLang, normalizeLang } from '@/i18n'

export const SETTINGS_QUERY_KEY = ['user-settings']
const GROUP_SCOPED_QUERY_KEYS = [
  ['balance'],
  ['transactions'],
  ['transfers'],
  ['debts'],
  ['workers'],
  ['workers-summary'],
  ['statistics'],
  ['group-members'],
  ['admin-members'],
  ['admin-workers-summary'],
]

const applyTheme = (theme?: 'light' | 'dark') => {
  const safeTheme = theme === 'dark' ? 'dark' : 'light'
  document.documentElement.dataset.theme = safeTheme
  document.body.dataset.theme = safeTheme
}

export const useAppSettings = () => {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: getUserSettings,
    staleTime: 30_000,
    retry: 1,
  })

  const settings = query.data || null
  const language = normalizeLang(settings?.language_code)
  const locale = localeFromLang(language)
  const theme = settings?.theme_preference === 'dark' ? 'dark' : 'light'

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const patchSettings = (next: UserSettings) => {
    queryClient.setQueryData<UserSettings>(SETTINGS_QUERY_KEY, next)
  }

  const invalidateGroupScopedData = async () => {
    await Promise.all(
      GROUP_SCOPED_QUERY_KEYS.map((queryKey) =>
        queryClient.invalidateQueries({ queryKey }),
      ),
    )
  }

  const languageMutation = useMutation({
    mutationFn: updateLanguage,
    onSuccess: patchSettings,
  })

  const currencyMutation = useMutation({
    mutationFn: updateCurrency,
    onSuccess: async (next) => {
      patchSettings(next)
      await invalidateGroupScopedData()
    },
  })

  const themeMutation = useMutation({
    mutationFn: updateTheme,
    onSuccess: patchSettings,
  })

  const activeGroupMutation = useMutation({
    mutationFn: updateActiveGroup,
    onSuccess: async (next) => {
      patchSettings(next)
      await invalidateGroupScopedData()
    },
  })

  const isMutating = useMemo(
    () =>
      languageMutation.isPending ||
      currencyMutation.isPending ||
      themeMutation.isPending ||
      activeGroupMutation.isPending,
    [
      activeGroupMutation.isPending,
      currencyMutation.isPending,
      languageMutation.isPending,
      themeMutation.isPending,
    ],
  )

  return {
    ...query,
    settings,
    language,
    locale,
    theme,
    isMutating,
    setLanguage: languageMutation.mutateAsync,
    setCurrency: currencyMutation.mutateAsync,
    setTheme: themeMutation.mutateAsync,
    setActiveGroup: activeGroupMutation.mutateAsync,
    refreshSettings: () => queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY }),
  }
}

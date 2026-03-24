import { useEffect, useState } from 'react'

interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    query_id?: string
    user?: {
      id: number
      first_name: string
      last_name?: string
      username?: string
      language_code?: string
    }
    auth_date?: number
    hash?: string
  }
  version: string
  platform: string
  colorScheme: 'light' | 'dark'
  themeParams: {
    bg_color?: string
    text_color?: string
    hint_color?: string
    link_color?: string
    button_color?: string
    button_text_color?: string
  }
  isExpanded: boolean
  viewportHeight: number
  viewportStableHeight: number
  headerColor: string
  backgroundColor: string
  BackButton: {
    isVisible: boolean
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
    show: () => void
    hide: () => void
  }
  MainButton: {
    text: string
    color: string
    textColor: string
    isVisible: boolean
    isActive: boolean
    isProgressVisible: boolean
    setText: (text: string) => void
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
    show: () => void
    hide: () => void
    enable: () => void
    disable: () => void
    showProgress: (leaveActive?: boolean) => void
    hideProgress: () => void
  }
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void
    selectionChanged: () => void
  }
  expand: () => void
  close: () => void
  ready: () => void
  sendData: (data: string) => void
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void
  openTelegramLink: (url: string) => void
  showPopup: (params: {
    title?: string
    message: string
    buttons?: Array<{ id?: string; type?: string; text?: string }>
  }, callback?: (id: string) => void) => void
  showAlert: (message: string, callback?: () => void) => void
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void
  enableClosingConfirmation: () => void
  disableClosingConfirmation: () => void
  setHeaderColor: (color: string) => void
  setBackgroundColor: (color: string) => void
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp
    }
  }
}

export const useTelegram = () => {
  const webApp = window.Telegram?.WebApp
  const [authReady, setAuthReady] = useState<boolean>(() => Boolean(webApp?.initData))

  useEffect(() => {
    if (!webApp) {
      setAuthReady(false)
      return
    }

    webApp.ready()
    if (webApp.initData) {
      setAuthReady(true)
      return
    }

    let cancelled = false
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      if (cancelled) return
      if (window.Telegram?.WebApp?.initData) {
        setAuthReady(true)
        window.clearInterval(timer)
        return
      }
      if (Date.now() - startedAt > 4000) {
        window.clearInterval(timer)
      }
    }, 120)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [webApp])

  const user = webApp?.initDataUnsafe?.user

  const haptic = {
    light: () => webApp?.HapticFeedback.impactOccurred('light'),
    medium: () => webApp?.HapticFeedback.impactOccurred('medium'),
    heavy: () => webApp?.HapticFeedback.impactOccurred('heavy'),
    success: () => webApp?.HapticFeedback.notificationOccurred('success'),
    error: () => webApp?.HapticFeedback.notificationOccurred('error'),
    warning: () => webApp?.HapticFeedback.notificationOccurred('warning'),
    selection: () => webApp?.HapticFeedback.selectionChanged(),
  }

  const showPopup = (message: string, buttons?: string[]) => {
    if (!webApp) return Promise.resolve(null)

    return new Promise<string | null>((resolve) => {
      webApp.showPopup(
        {
          message,
          buttons: buttons?.map((text, id) => ({ id: String(id), text })),
        },
        (buttonId) => resolve(buttonId)
      )
    })
  }

  const showAlert = (message: string) => {
    return new Promise<void>((resolve) => {
      webApp?.showAlert(message, () => resolve())
    })
  }

  const showConfirm = (message: string) => {
    return new Promise<boolean>((resolve) => {
      webApp?.showConfirm(message, (confirmed) => resolve(confirmed))
    })
  }

  return {
    webApp,
    initData: webApp?.initData || '',
    authReady,
    user,
    platform: webApp?.platform,
    colorScheme: webApp?.colorScheme || 'light',
    themeParams: webApp?.themeParams,
    haptic,
    showPopup,
    showAlert,
    showConfirm,
    close: () => webApp?.close(),
    sendData: (data: any) => webApp?.sendData(JSON.stringify(data)),
  }
}

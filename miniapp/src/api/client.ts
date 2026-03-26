import axios from 'axios'

const ACT_AS_STORAGE_KEY = 'expense-bot-act-as-user'
const envBase = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || ''
const API_BASE_URL = envBase
  ? envBase.replace(/\/$/, '')
  : `${window.location.origin.replace(/\/$/, '')}/api`

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
})

export const getActAsUserId = () => {
  const raw = window.localStorage.getItem(ACT_AS_STORAGE_KEY)
  if (!raw) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

export const setActAsUserId = (userId: number) => {
  window.localStorage.setItem(ACT_AS_STORAGE_KEY, String(userId))
}

export const clearActAsUserId = () => {
  window.localStorage.removeItem(ACT_AS_STORAGE_KEY)
}

apiClient.interceptors.request.use((config) => {
  const webApp = window.Telegram?.WebApp
  if (webApp?.initData) {
    config.headers['X-Telegram-Init-Data'] = webApp.initData
  }
  const actAsUserId = getActAsUserId()
  if (actAsUserId) {
    config.headers['X-Act-As-User'] = String(actAsUserId)
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const webApp = window.Telegram?.WebApp
    if (error.response?.status === 401 && webApp?.initData) {
      const lang = (webApp.initDataUnsafe?.user?.language_code || 'uz').toLowerCase()
      const message = lang.startsWith('ru')
        ? 'Ошибка авторизации. Перезапустите приложение.'
        : lang.startsWith('en')
          ? 'Authorization error. Please reopen the app.'
          : 'Avtorizatsiya xatosi. Iltimos, ilovani qayta oching.'
      webApp.showAlert(message)
    }
    return Promise.reject(error)
  }
)

export default apiClient
export { apiClient }

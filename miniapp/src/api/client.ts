import axios from 'axios'

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

apiClient.interceptors.request.use((config) => {
  const webApp = window.Telegram?.WebApp
  if (webApp?.initData) {
    config.headers['X-Telegram-Init-Data'] = webApp.initData
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

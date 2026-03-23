import { format } from 'date-fns'
import { AppLang, localeFromLang } from '@/i18n'

export const formatMoney = (amount: number, currency: string, locale?: string) => {
  try {
    return new Intl.NumberFormat(locale || 'uz-UZ', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount) + ` ${currency}`
  } catch {
    return `${amount.toFixed(2)} ${currency}`
  }
}

export const formatDateTime = (value?: string, lang: AppLang = 'uz') => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  try {
    return new Intl.DateTimeFormat(localeFromLang(lang), {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return format(date, 'dd.MM.yyyy HH:mm')
  }
}

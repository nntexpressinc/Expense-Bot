const UNKNOWN_CATEGORY_NAMES = new Set([
  "noma'lum",
  'неизвестно',
  'unknown',
])

type TransactionDisplayCategory = {
  name?: string | null
  icon?: string | null
}

type TransactionDisplayItem = {
  category?: TransactionDisplayCategory | null
  description?: string | null
}

const normalizeValue = (value?: string | null): string => {
  return (value || '').trim().toLowerCase()
}

export const hasMeaningfulCategory = (transaction: Pick<TransactionDisplayItem, 'category'>): boolean => {
  const name = normalizeValue(transaction.category?.name)
  return Boolean(name) && !UNKNOWN_CATEGORY_NAMES.has(name)
}

export const getTransactionDisplayTitle = (
  transaction: Pick<TransactionDisplayItem, 'category' | 'description'>,
  fallbackTitle: string,
): string => {
  if (hasMeaningfulCategory(transaction)) {
    const icon = transaction.category?.icon ? `${transaction.category.icon} ` : ''
    return `${icon}${transaction.category?.name || ''}`.trim()
  }

  const description = transaction.description?.trim()
  if (description) {
    return description
  }

  return fallbackTitle
}

export const shouldShowTransactionDescription = (
  transaction: Pick<TransactionDisplayItem, 'description'>,
  title: string,
): boolean => {
  const description = transaction.description?.trim()
  return Boolean(description) && description !== title.trim()
}

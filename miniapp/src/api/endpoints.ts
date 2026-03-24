import apiClient from './client'

export interface UserGroup {
  id: number
  name: string
  role: 'admin' | 'member'
  joined_at?: string | null
}

export interface UserSettings {
  id: number
  username?: string
  first_name: string
  last_name?: string
  language_code: string
  default_currency: string
  theme_preference: 'light' | 'dark'
  is_admin: boolean
  is_group_admin: boolean
  active_group_id?: number | null
  active_group_name?: string | null
  groups: UserGroup[]
}

export interface Balance {
  total_balance: number
  own_balance: number
  received_balance: number
  debt_balance: number
  outstanding_debt_balance: number
  currency: string
  group_id?: number
  group_name?: string
}

export interface Category {
  id: number
  name: string
  type: 'income' | 'expense'
  icon: string
  is_system: boolean
}

export interface Transaction {
  id: string
  type: 'income' | 'expense' | 'transfer_out' | 'transfer_in' | 'debt' | 'debt_payment'
  amount: number
  currency: string
  funding_source?: 'main' | 'debt'
  debt_kind?: 'cash_loan' | 'credit_purchase' | null
  debt_source_name?: string | null
  debt_used_amount?: number | null
  main_used_amount?: number | null
  category?: {
    id: number
    name: string
    icon: string
  }
  description?: string
  attachment_file_id?: string
  attachment_type?: 'photo' | 'document'
  attachment_name?: string
  transaction_date: string
  created_at: string
}

export interface Transfer {
  id: string
  sender_id: number
  recipient_id: number
  recipient_username?: string
  recipient_name?: string
  amount: number
  currency: string
  description?: string
  status: 'pending' | 'completed' | 'cancelled'
  remaining_amount: number
  original_amount?: number
  original_currency?: string
  expenses?: Array<{
    id: string
    amount: number
    currency: string
    category: {
      id?: number
      name: string
      icon?: string
    }
    description?: string
    created_at: string
  }>
  created_at: string
}

export interface TransferGroup {
  recipient_id: number
  recipient_username?: string
  recipient_name: string
  transfer_count: number
  amount: number
  remaining_amount: number
  spent_amount: number
  currency: string
  last_transfer_at: string
}

export interface TransferGroupDetail extends TransferGroup {
  transfers: Array<{
    id: string
    amount: number
    remaining_amount: number
    spent_amount: number
    currency: string
    status: 'pending' | 'completed' | 'cancelled'
    description?: string
    created_at: string
  }>
  expenses: Array<{
    id: string
    transfer_id: string
    amount: number
    currency: string
    category: {
      id?: number
      name: string
      icon?: string
    }
    description?: string
    created_at: string
  }>
}

export interface TransferRecipient {
  id: number
  username?: string
  first_name: string
  last_name?: string
  display_name: string
}

export interface Statistics {
  period: string
  total_income: number
  total_expense: number
  difference: number
  top_categories: Array<{
    name: string
    icon: string
    amount: number
    percent: number
  }>
}

export interface DebtRepayment {
  id?: string
  amount: number
  currency: string
  converted_amount?: number
  note?: string
  repaid_at?: string
}

export interface Debt {
  id: string
  kind: 'cash_loan' | 'credit_purchase'
  amount: number
  remaining: number
  used?: number
  available_to_spend?: number
  affects_main_balance?: boolean
  currency: string
  description?: string
  source_name?: string
  source_contact?: string
  reference?: string
  note?: string
  status?: 'active' | 'partially_repaid' | 'fully_repaid' | 'archived'
  created_at: string
  paid_at?: string | null
  repayments?: DebtRepayment[]
}

export interface Worker {
  id: string
  full_name: string
  phone?: string
  role_name?: string
  payment_type: 'daily' | 'monthly' | 'volume'
  rate: number
  currency: string
  start_date: string
  is_active: boolean
  notes?: string
  today_status?: 'present' | 'absent' | 'half_day' | 'custom' | null
  today_units?: number
}

export interface WorkerSummary {
  worker_id: string
  full_name: string
  payment_type: 'daily' | 'monthly' | 'volume'
  currency: string
  base_amount: number
  advance_amount: number
  paid_amount: number
  payable_amount: number
  quantity?: number
  attendance_count?: number
  advances_count?: number
  payments_count?: number
  status: 'unpaid' | 'partial' | 'paid'
}

export interface GroupMember {
  user_id: number
  username?: string
  first_name: string
  last_name?: string
  role: 'admin' | 'member'
}

export const getUserSettings = () => apiClient.get<UserSettings>('/settings/user').then((res) => res.data)
export const updateLanguage = (language: string) =>
  apiClient.patch<UserSettings>('/settings/user/language', { language }).then((res) => res.data)
export const updateCurrency = (currency: 'UZS' | 'USD') =>
  apiClient.patch<UserSettings>('/settings/user/currency', { currency }).then((res) => res.data)
export const updateTheme = (theme: 'light' | 'dark') =>
  apiClient.patch<UserSettings>('/settings/user/theme', { theme }).then((res) => res.data)
export const updateActiveGroup = (group_id: number) =>
  apiClient.patch<UserSettings>('/settings/user/active-group', { group_id }).then((res) => res.data)

export const getBalance = () => apiClient.get<Balance>('/settings/balance').then((res) => res.data)
export const getCategories = (type?: 'income' | 'expense') =>
  apiClient.get<Category[]>('/settings/categories', { params: { type } }).then((res) => res.data)

export const getTransactions = (params?: {
  limit?: number
  offset?: number
  type?: string
  category_id?: number
  start_date?: string
  end_date?: string
}) => apiClient.get<Transaction[]>('/transactions/', { params }).then((res) => res.data)

export const createTransaction = (data: {
  type: 'income' | 'expense'
  amount: number
  currency?: string
  category_id?: number
  description?: string
  funding_source?: 'main' | 'debt'
  debt_id?: string
  attachment_file_id?: string
  attachment_type?: 'photo' | 'document'
  attachment_name?: string
}) => apiClient.post<Transaction>('/transactions/', data).then((res) => res.data)

export const deleteTransaction = (id: string) =>
  apiClient.delete(`/transactions/${id}`).then((res) => res.data)

export const getTransfers = (type: 'sent' | 'received') =>
  apiClient.get<Transfer[]>(`/transfers/${type}`).then((res) => res.data)
export const getSentTransferGroups = (params?: { limit?: number; offset?: number }) =>
  apiClient.get<TransferGroup[]>('/transfers/sent/grouped', { params }).then((res) => res.data)
export const getSentTransferGroupDetails = (recipientId: number) =>
  apiClient.get<TransferGroupDetail>(`/transfers/sent/grouped/${recipientId}`).then((res) => res.data)
export const createTransfer = (data: {
  recipient_username?: string
  recipient_telegram_id?: number
  amount: number
  currency?: string
  description?: string
}) => apiClient.post<Transfer>('/transfers/', data).then((res) => res.data)
export const getTransferRecipients = (params?: { search?: string; limit?: number }) =>
  apiClient.get<TransferRecipient[]>('/transfers/recipients', { params }).then((res) => res.data)
export const getTransferDetails = (id: string) =>
  apiClient.get<Transfer>(`/transfers/${id}`).then((res) => res.data)

export const getStatistics = (period?: 'day' | 'week' | 'month' | 'year') =>
  apiClient.get<Statistics>('/statistics/', { params: { period } }).then((res) => res.data)
export const exportStatisticsExcel = (period?: 'day' | 'week' | 'month' | 'year') =>
  apiClient.get('/statistics/export/excel', { params: { period }, responseType: 'blob' }).then((res) => res.data as Blob)

export const listDebts = () => apiClient.get<Debt[]>('/debts/').then((res) => res.data)
export const createDebt = (data: {
  amount: number
  kind?: 'cash_loan' | 'credit_purchase'
  currency?: string
  description?: string
  source_name?: string
  source_contact?: string
  reference?: string
  note?: string
}) => apiClient.post<Debt>('/debts/', data).then((res) => res.data)
export const payDebt = (debtId: string, data: { amount: number; currency?: string; note?: string }) =>
  apiClient.post<Debt>(`/debts/${debtId}/pay`, data).then((res) => res.data)

export const getGroups = () => apiClient.get<UserGroup[]>('/groups/').then((res) => res.data)
export const createGroup = (name: string) => apiClient.post('/groups/', { name }).then((res) => res.data)
export const renameGroup = (groupId: number, name: string) =>
  apiClient.patch(`/groups/${groupId}`, { name }).then((res) => res.data)
export const getGroupMembers = (groupId: number) =>
  apiClient.get<GroupMember[]>(`/groups/${groupId}/members`).then((res) => res.data)
export const upsertGroupMember = (groupId: number, user_id: number, role: 'admin' | 'member') =>
  apiClient.post(`/groups/${groupId}/members`, { user_id, role }).then((res) => res.data)
export const removeGroupMember = (groupId: number, userId: number) =>
  apiClient.delete(`/groups/${groupId}/members/${userId}`).then((res) => res.data)

export const listWorkers = (params?: { include_inactive?: boolean }) =>
  apiClient.get<Worker[]>('/workers/', { params }).then((res) => res.data)
export const createWorker = (data: {
  full_name: string
  phone?: string
  role_name?: string
  payment_type: 'daily' | 'monthly' | 'volume'
  rate: number
  currency?: 'UZS' | 'USD'
  start_date: string
  notes?: string
}) => apiClient.post<Worker>('/workers/', data).then((res) => res.data)
export const createAttendance = (
  workerId: string,
  data: { entry_date: string; status: 'present' | 'absent' | 'half_day' | 'custom'; units: number; comment?: string },
) => apiClient.post(`/workers/${workerId}/attendance`, data).then((res) => res.data)
export const createWorkerAdvance = (
  workerId: string,
  data: { amount: number; currency?: 'UZS' | 'USD'; note?: string; payment_date: string },
) => apiClient.post(`/workers/${workerId}/advances`, data).then((res) => res.data)
export const createWorkerPayment = (
  workerId: string,
  data: { amount: number; currency?: 'UZS' | 'USD'; note?: string; payment_date: string },
) => apiClient.post(`/workers/${workerId}/payments`, data).then((res) => res.data)
export const getWorkerSummary = (workerId: string, start_date: string, end_date: string) =>
  apiClient.get<WorkerSummary>(`/workers/${workerId}/summary`, { params: { start_date, end_date } }).then((res) => res.data)
export const getWorkersSummary = (params: { start_date: string; end_date: string; include_inactive?: boolean }) =>
  apiClient.get<{ workers: WorkerSummary[]; totals: Record<string, number | string> }>('/workers/summary', { params }).then((res) => res.data)

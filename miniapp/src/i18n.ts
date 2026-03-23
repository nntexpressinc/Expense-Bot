export type AppLang = 'uz' | 'ru' | 'en'

export const normalizeLang = (value?: string): AppLang => {
  const lang = (value || 'uz').toLowerCase()
  if (lang.startsWith('ru')) return 'ru'
  if (lang.startsWith('en')) return 'en'
  return 'uz'
}

export const localeFromLang = (lang?: string): string => {
  const normalized = normalizeLang(lang)
  if (normalized === 'ru') return 'ru-RU'
  if (normalized === 'en') return 'en-US'
  return 'uz-UZ'
}

type Dict = Record<AppLang, string>

const translations = {
  loading: { uz: 'Yuklanmoqda...', ru: 'Р—Р°РіСЂСѓР·РєР°...', en: 'Loading...' },
  notLoaded: { uz: "Ma'lumot yuklanmadi", ru: 'Р”Р°РЅРЅС‹Рµ РЅРµ Р·Р°РіСЂСѓР·РёР»РёСЃСЊ', en: 'Data was not loaded' },
  retry: { uz: 'Qayta urinish', ru: 'РџРѕРІС‚РѕСЂРёС‚СЊ', en: 'Retry' },
  home: { uz: 'Bosh sahifa', ru: 'Р“Р»Р°РІРЅР°СЏ', en: 'Home' },
  activity: { uz: 'Operatsiyalar', ru: 'РћРїРµСЂР°С†РёРё', en: 'Activity' },
  transfers: { uz: 'OвЂtkazmalar', ru: 'РџРµСЂРµРІРѕРґС‹', en: 'Transfers' },
  debts: { uz: 'Qarzlar', ru: 'Р”РѕР»РіРё', en: 'Debts' },
  team: { uz: 'Ishchilar', ru: 'РЎРѕС‚СЂСѓРґРЅРёРєРё', en: 'Team' },
  settings: { uz: 'Sozlamalar', ru: 'РќР°СЃС‚СЂРѕР№РєРё', en: 'Settings' },
  statistics: { uz: 'Statistika', ru: 'РЎС‚Р°С‚РёСЃС‚РёРєР°', en: 'Statistics' },
  reports: { uz: 'Hisobotlar', ru: 'РћС‚С‡С‘С‚С‹', en: 'Reports' },
  admin: { uz: 'Boshqaruv', ru: 'РЈРїСЂР°РІР»РµРЅРёРµ', en: 'Admin' },
  currentGroup: { uz: 'Faol guruh', ru: 'РђРєС‚РёРІРЅР°СЏ РіСЂСѓРїРїР°', en: 'Active group' },
  totalBalance: { uz: 'Jami balans', ru: 'РћР±С‰РёР№ Р±Р°Р»Р°РЅСЃ', en: 'Total balance' },
  ownBalance: { uz: 'OвЂz mablagвЂi', ru: 'РЎРѕР±СЃС‚РІРµРЅРЅС‹Рµ СЃСЂРµРґСЃС‚РІР°', en: 'Own balance' },
  receivedBalance: { uz: 'Qabul qilingan', ru: 'РџРѕР»СѓС‡РµРЅРѕ', en: 'Received balance' },
  debtBalance: { uz: 'Qarz limiti', ru: 'Р”РѕР»РіРѕРІРѕР№ Р»РёРјРёС‚', en: 'Debt balance' },
  outstandingDebt: { uz: 'Qolgan qarz', ru: 'РћСЃС‚Р°С‚РѕРє РґРѕР»РіР°', en: 'Outstanding debt' },
  quickActions: { uz: 'Tezkor amallar', ru: 'Р‘С‹СЃС‚СЂС‹Рµ РґРµР№СЃС‚РІРёСЏ', en: 'Quick actions' },
  addIncome: { uz: 'Kirim qoвЂshish', ru: 'Р”РѕР±Р°РІРёС‚СЊ РґРѕС…РѕРґ', en: 'Add income' },
  addExpense: { uz: 'Chiqim qoвЂshish', ru: 'Р”РѕР±Р°РІРёС‚СЊ СЂР°СЃС…РѕРґ', en: 'Add expense' },
  createTransfer: { uz: 'Pul oвЂtkazish', ru: 'РЎРґРµР»Р°С‚СЊ РїРµСЂРµРІРѕРґ', en: 'Create transfer' },
  manageDebts: { uz: 'Qarzlarni boshqarish', ru: 'РЈРїСЂР°РІР»СЏС‚СЊ РґРѕР»РіР°РјРё', en: 'Manage debts' },
  openStatistics: { uz: 'Statistikani ochish', ru: 'РћС‚РєСЂС‹С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ', en: 'Open statistics' },
  manageWorkers: { uz: 'Ishchilarni boshqarish', ru: 'РЈРїСЂР°РІР»СЏС‚СЊ СЃРѕС‚СЂСѓРґРЅРёРєР°РјРё', en: 'Manage workers' },
  exportExcel: { uz: 'Excel yuklash', ru: 'РЎРєР°С‡Р°С‚СЊ Excel', en: 'Export Excel' },
  recentOperations: { uz: 'SoвЂnggi operatsiyalar', ru: 'РџРѕСЃР»РµРґРЅРёРµ РѕРїРµСЂР°С†РёРё', en: 'Recent operations' },
  noOperations: { uz: 'Operatsiyalar yoвЂq', ru: 'РћРїРµСЂР°С†РёР№ РЅРµС‚', en: 'No operations yet' },
  amount: { uz: 'Summa', ru: 'РЎСѓРјРјР°', en: 'Amount' },
  currency: { uz: 'Valyuta', ru: 'Р’Р°Р»СЋС‚Р°', en: 'Currency' },
  description: { uz: 'Izoh', ru: 'РћРїРёСЃР°РЅРёРµ', en: 'Description' },
  save: { uz: 'Saqlash', ru: 'РЎРѕС…СЂР°РЅРёС‚СЊ', en: 'Save' },
  send: { uz: 'Yuborish', ru: 'РћС‚РїСЂР°РІРёС‚СЊ', en: 'Send' },
  pay: { uz: 'ToвЂlash', ru: 'РџРѕРіР°СЃРёС‚СЊ', en: 'Pay' },
  income: { uz: 'Kirim', ru: 'Р”РѕС…РѕРґ', en: 'Income' },
  expense: { uz: 'Chiqim', ru: 'Р Р°СЃС…РѕРґ', en: 'Expense' },
  mainSource: { uz: 'Asosiy balans', ru: 'РћСЃРЅРѕРІРЅРѕР№ Р±Р°Р»Р°РЅСЃ', en: 'Main balance' },
  debtSource: { uz: 'Qarz manbasi', ru: 'РСЃС‚РѕС‡РЅРёРє РґРѕР»РіР°', en: 'Debt source' },
  selectDebt: { uz: 'Qarzni tanlang', ru: 'Выберите долг', en: 'Select debt' },
  debtType: { uz: 'Qarz turi', ru: 'Тип долга', en: 'Debt type' },
  cashLoan: { uz: 'Naqd qarz olish', ru: 'Взять деньги в долг', en: 'Borrow cash' },
  creditPurchase: { uz: 'Qarzga xarid', ru: 'Купить в долг', en: 'Buy on credit' },
  cashLoanHint: { uz: 'Bu summa asosiy balansga tushadi', ru: 'Эта сумма попадёт в основной баланс', en: 'This amount goes to main balance' },
  creditPurchaseHint: { uz: 'Bu qarz faqat xarajat uchun manba bo‘ladi', ru: 'Этот долг будет источником только для расходов', en: 'This debt will only be used as an expense source' },
  noDebtSources: { uz: 'Xarajat uchun qarz manbasi yo‘q', ru: 'Нет доступных долгов для расходов', en: 'No debt sources available for expenses' },
  debtRepaymentOnly: { uz: 'Faqat qaytarish uchun', ru: 'Только для погашения', en: 'Repayment only' },
  chooseRecipient: { uz: 'Qabul qiluvchini tanlang', ru: 'Р’С‹Р±РµСЂРёС‚Рµ РїРѕР»СѓС‡Р°С‚РµР»СЏ', en: 'Choose recipient' },
  recipient: { uz: 'Qabul qiluvchi', ru: 'РџРѕР»СѓС‡Р°С‚РµР»СЊ', en: 'Recipient' },
  sent: { uz: 'Yuborilgan', ru: 'РћС‚РїСЂР°РІР»РµРЅРѕ', en: 'Sent' },
  received: { uz: 'Qabul qilingan', ru: 'РџРѕР»СѓС‡РµРЅРѕ', en: 'Received' },
  noRecipients: { uz: 'Bu guruhda boshqa foydalanuvchi yoвЂq', ru: 'Р’ СЌС‚РѕР№ РіСЂСѓРїРїРµ РїРѕРєР° РЅРµС‚ РґСЂСѓРіРёС… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№', en: 'There are no other users in this group' },
  debtList: { uz: 'Qarzlar roвЂyxati', ru: 'РЎРїРёСЃРѕРє РґРѕР»РіРѕРІ', en: 'Debt list' },
  createDebt: { uz: 'Qarz qoвЂshish', ru: 'Р”РѕР±Р°РІРёС‚СЊ РґРѕР»Рі', en: 'Add debt' },
  remaining: { uz: 'Qoldiq', ru: 'РћСЃС‚Р°С‚РѕРє', en: 'Remaining' },
  availableToSpend: { uz: 'Ishlatish mumkin', ru: 'Р”РѕСЃС‚СѓРїРЅРѕ Рє РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЋ', en: 'Available to spend' },
  sourceName: { uz: 'Kimdan olindi', ru: 'РљСЂРµРґРёС‚РѕСЂ', en: 'Source / lender' },
  sourceContact: { uz: 'Kontakt', ru: 'РљРѕРЅС‚Р°РєС‚', en: 'Contact' },
  reference: { uz: 'Hujjat / reference', ru: 'Р РµС„РµСЂРµРЅСЃ', en: 'Reference' },
  note: { uz: 'QoвЂshimcha eslatma', ru: 'РџСЂРёРјРµС‡Р°РЅРёРµ', en: 'Note' },
  workers: { uz: 'Ishchilar', ru: 'РЎРѕС‚СЂСѓРґРЅРёРєРё', en: 'Workers' },
  addWorker: { uz: 'Ishchi qoвЂshish', ru: 'Р”РѕР±Р°РІРёС‚СЊ СЃРѕС‚СЂСѓРґРЅРёРєР°', en: 'Add worker' },
  fullName: { uz: 'ToвЂliq ism', ru: 'РџРѕР»РЅРѕРµ РёРјСЏ', en: 'Full name' },
  phone: { uz: 'Telefon', ru: 'РўРµР»РµС„РѕРЅ', en: 'Phone' },
  roleName: { uz: 'Vazifa', ru: 'Р РѕР»СЊ', en: 'Role' },
  paymentType: { uz: 'ToвЂlov turi', ru: 'РўРёРї РѕРїР»Р°С‚С‹', en: 'Payment type' },
  daily: { uz: 'Kunlik', ru: 'РџРѕРґРЅРµРІРЅС‹Р№', en: 'Daily' },
  monthly: { uz: 'Oylik', ru: 'РњРµСЃСЏС‡РЅС‹Р№', en: 'Monthly' },
  volume: { uz: 'Hajm boвЂyicha', ru: 'РЎРґРµР»СЊРЅС‹Р№', en: 'Volume-based' },
  startDate: { uz: 'Boshlagan sana', ru: 'Р”Р°С‚Р° РЅР°С‡Р°Р»Р°', en: 'Start date' },
  attendance: { uz: 'Davomat', ru: 'РџРѕСЃРµС‰Р°РµРјРѕСЃС‚СЊ', en: 'Attendance' },
  advances: { uz: 'Avanslar', ru: 'РђРІР°РЅСЃС‹', en: 'Advances' },
  payments: { uz: 'ToвЂlovlar', ru: 'Р’С‹РїР»Р°С‚С‹', en: 'Payments' },
  payable: { uz: 'ToвЂlanadigan summa', ru: 'Рљ РІС‹РїР»Р°С‚Рµ', en: 'Payable amount' },
  present: { uz: 'Keldi', ru: 'РџСЂРёСЃСѓС‚СЃС‚РІРѕРІР°Р»', en: 'Present' },
  absent: { uz: 'Kelmadi', ru: 'РћС‚СЃСѓС‚СЃС‚РІРѕРІР°Р»', en: 'Absent' },
  halfDay: { uz: 'Yarim kun', ru: 'РџРѕР»РґРЅСЏ', en: 'Half-day' },
  customUnits: { uz: 'Birliklar', ru: 'Р•РґРёРЅРёС†С‹', en: 'Units' },
  comment: { uz: 'Izoh', ru: 'РљРѕРјРјРµРЅС‚Р°СЂРёР№', en: 'Comment' },
  recordAttendance: { uz: 'Davomat kiritish', ru: 'РћС‚РјРµС‚РёС‚СЊ РїРѕСЃРµС‰Р°РµРјРѕСЃС‚СЊ', en: 'Record attendance' },
  recordAdvance: { uz: 'Avans yozish', ru: 'Р—Р°РїРёСЃР°С‚СЊ Р°РІР°РЅСЃ', en: 'Record advance' },
  recordPayment: { uz: 'ToвЂlov yozish', ru: 'Р—Р°РїРёСЃР°С‚СЊ РІС‹РїР»Р°С‚Сѓ', en: 'Record payment' },
  language: { uz: 'Til', ru: 'РЇР·С‹Рє', en: 'Language' },
  theme: { uz: 'Mavzu', ru: 'РўРµРјР°', en: 'Theme' },
  lightTheme: { uz: 'YorugвЂ', ru: 'РЎРІРµС‚Р»Р°СЏ', en: 'Light' },
  darkTheme: { uz: 'QorongвЂi', ru: 'РўС‘РјРЅР°СЏ', en: 'Dark' },
  createNewGroup: { uz: 'Yangi guruh', ru: 'РќРѕРІР°СЏ РіСЂСѓРїРїР°', en: 'New group' },
  groupName: { uz: 'Guruh nomi', ru: 'РќР°Р·РІР°РЅРёРµ РіСЂСѓРїРїС‹', en: 'Group name' },
  rename: { uz: 'Nomini oвЂzgartirish', ru: 'РџРµСЂРµРёРјРµРЅРѕРІР°С‚СЊ', en: 'Rename' },
  members: { uz: 'AвЂ™zolar', ru: 'РЈС‡Р°СЃС‚РЅРёРєРё', en: 'Members' },
  addMember: { uz: 'AвЂ™zo qoвЂshish', ru: 'Р”РѕР±Р°РІРёС‚СЊ СѓС‡Р°СЃС‚РЅРёРєР°', en: 'Add member' },
  userId: { uz: 'Foydalanuvchi ID', ru: 'ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ', en: 'User ID' },
  role: { uz: 'Rol', ru: 'Р РѕР»СЊ', en: 'Role' },
  member: { uz: 'AвЂ™zo', ru: 'РЈС‡Р°СЃС‚РЅРёРє', en: 'Member' },
  groupAdmin: { uz: 'Guruh admini', ru: 'РђРґРјРёРЅ РіСЂСѓРїРїС‹', en: 'Group admin' },
  superAdmin: { uz: 'Super admin', ru: 'РЎСѓРїРµСЂ Р°РґРјРёРЅ', en: 'Super admin' },
  noGroups: { uz: 'Siz hali hech bir guruhga ulanmagansiz', ru: 'Р’С‹ РїРѕРєР° РЅРµ РїРѕРґРєР»СЋС‡РµРЅС‹ РЅРё Рє РѕРґРЅРѕР№ РіСЂСѓРїРїРµ', en: 'You are not connected to any group yet' },
  noDebts: { uz: 'Qarzlar yoвЂq', ru: 'Р”РѕР»РіРѕРІ РЅРµС‚', en: 'No debts' },
  noWorkers: { uz: 'Ishchilar yoвЂq', ru: 'РЎРѕС‚СЂСѓРґРЅРёРєРѕРІ РЅРµС‚', en: 'No workers' },
  notAllowed: { uz: 'Bu boвЂlim faqat admin uchun', ru: 'Р­С‚РѕС‚ СЂР°Р·РґРµР» РґРѕСЃС‚СѓРїРµРЅ С‚РѕР»СЊРєРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ', en: 'This section is for admins only' },
  successSaved: { uz: 'Saqlandi', ru: 'РЎРѕС…СЂР°РЅРµРЅРѕ', en: 'Saved' },
  requestFailed: { uz: 'SoвЂrov bajarilmadi', ru: 'РќРµ СѓРґР°Р»РѕСЃСЊ РІС‹РїРѕР»РЅРёС‚СЊ Р·Р°РїСЂРѕСЃ', en: 'Request failed' },
  remove: { uz: 'Olib tashlash', ru: 'РЈРґР°Р»РёС‚СЊ', en: 'Remove' },
  choosePeriod: { uz: 'Davrni tanlang', ru: 'Р’С‹Р±РµСЂРёС‚Рµ РїРµСЂРёРѕРґ', en: 'Choose period' },
  day: { uz: 'Kun', ru: 'Р”РµРЅСЊ', en: 'Day' },
  week: { uz: 'Hafta', ru: 'РќРµРґРµР»СЏ', en: 'Week' },
  month: { uz: 'Oy', ru: 'РњРµСЃСЏС†', en: 'Month' },
  year: { uz: 'Yil', ru: 'Р“РѕРґ', en: 'Year' },
} satisfies Record<string, Dict>

export type TranslationKey = keyof typeof translations

export const t = (key: TranslationKey, lang: AppLang): string => {
  return translations[key]?.[lang] || translations[key]?.uz || key
}




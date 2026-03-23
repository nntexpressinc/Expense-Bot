# 📱 Expenses Bot Mini App

Modern Telegram Mini App for personal finance management.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🛠️ Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **@tanstack/react-query** - Data fetching
- **Zustand** - State management
- **Recharts** - Charts
- **Axios** - HTTP client
- **React Router** - Routing

## 📁 Structure

```
src/
├── api/              # API client and endpoints
├── components/       # React components
│   ├── Dashboard.tsx
│   ├── Transactions.tsx
│   ├── Transfers.tsx
│   ├── Statistics.tsx
│   ├── Settings.tsx
│   └── shared/
│       └── BottomNav.tsx
├── hooks/           # Custom hooks
│   └── useTelegram.ts
├── App.tsx          # Main component
├── main.tsx         # Entry point
└── index.css        # Global styles
```

## 🔧 Configuration

Create `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## 📱 Features

### Dashboard
- Balance overview (total/own/received)
- Monthly statistics
- Top 3 categories
- Recent transactions
- Quick actions

### Transactions
- Transaction list
- Filters (all/income/expense)
- Category icons
- Delete transactions

### Transfers
- Sent/received tabs
- Transfer status
- Spending progress
- Expense details

### Statistics
- Period selector (day/week/month/year)
- Bar chart (income vs expense)
- Pie chart (categories)
- Detailed breakdown

### Settings
- User profile
- Currency settings
- Language selection
- Category management
- Export data

## 🎨 Styling

Using TailwindCSS with custom theme:

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: '#3b82f6',    // Blue
      secondary: '#8b5cf6',  // Purple
      success: '#22c55e',    // Green
      danger: '#ef4444',     // Red
      warning: '#f59e0b',    // Orange
    }
  }
}
```

## 🔐 Authentication

All requests automatically include Telegram WebApp init data:

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

apiClient.interceptors.request.use((config) => {
  const initData = window.Telegram?.WebApp?.initData
  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData
  }
  return config
})
```

## 📡 API Integration

Using React Query for efficient data fetching:

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['balance'],
  queryFn: getBalance,
  refetchInterval: 30000, // Refetch every 30 seconds
})
```

## 🎯 Telegram WebApp Integration

Custom hook for Telegram WebApp API:

```typescript
const { webApp, user, haptic, showPopup } = useTelegram()

// Haptic feedback
haptic.success()
haptic.error()
haptic.heavy()

// Popups
await showPopup({
  title: 'Success',
  message: 'Transaction created!',
  buttons: [{ type: 'ok' }]
})
```

## 📱 Testing in Telegram

### Local testing with ngrok

1. Install [ngrok](https://ngrok.com/)
2. Run dev server: `npm run dev`
3. Create tunnel: `ngrok http 3000`
4. Register URL in BotFather
5. Open bot and click Mini App button

## 🚀 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Set environment variables:
- `VITE_API_BASE_URL`: Your API URL

### Other platforms
- Netlify
- Cloudflare Pages
- GitHub Pages
- Any static hosting

## 📚 Documentation

- [Setup Guide](../MINIAPP_SETUP.md)
- [API Documentation](../docs/MINIAPP_API.md)
- [Architecture](../docs/ARCHITECTURE.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -m "feat: add new feature"`
4. Push to branch: `git push origin feature/new-feature`
5. Create Pull Request

## 📄 License

MIT License

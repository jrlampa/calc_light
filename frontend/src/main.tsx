import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast: 'bg-white/90 backdrop-blur-md border border-white/60 shadow-lg rounded-xl text-slate-700',
            success: '!text-emerald-700',
            error: '!text-red-600',
          },
        }}
        richColors
        closeButton
      />
    </QueryClientProvider>
  </StrictMode>,
)


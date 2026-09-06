import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import RuleStudio from './pages/RuleStudio.tsx'
import './index.css'
import App from './App.tsx'
import Login from './pages/login.tsx'
import { ProtectedRoute } from './components/ProtectedRoute.tsx'
import DebarmentIndex from "./pages/DebarmentIndex.tsx"

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
<Routes>
  <Route path="/rules" element={<ProtectedRoute><RuleStudio /></ProtectedRoute>} />
  <Route path="/" element={<Login />} />
  <Route path="/dashboard" element={<ProtectedRoute><App /></ProtectedRoute>} />
  <Route path="/debarment" element={<ProtectedRoute><DebarmentIndex /></ProtectedRoute>} />
</Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
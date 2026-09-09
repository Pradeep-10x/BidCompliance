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
import AuditTrail from './pages/AuditTrail.tsx'
import BidderDetail from './pages/BidderDetail.tsx'
import Tenders from './pages/Tenders.tsx'
import Notifications from './pages/Notifications.tsx'
import Dossiers from './pages/Dossiers.tsx'
import Admin from './pages/Admin.tsx'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
<Routes>
  <Route path="/tenders" element={<ProtectedRoute><Tenders /></ProtectedRoute>} />
<Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
<Route path="/dossiers" element={<ProtectedRoute><Dossiers /></ProtectedRoute>} />
<Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
  <Route path="/bidders/:bidderId" element={<ProtectedRoute><BidderDetail /></ProtectedRoute>} />
  <Route path="/audit" element={<ProtectedRoute><AuditTrail /></ProtectedRoute>} />
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
import { useSearchParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { SectionCards } from "@/components/section-cards"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"

function App() {
  const [searchParams] = useSearchParams()
  const tenderId = searchParams.get("tenderId")

  const { data: bidders } = useQuery({
    queryKey: ["bidders", tenderId],
    queryFn: () => apiFetch(`/bidders${tenderId ? `?tenderId=${tenderId}` : ""}`),
  })

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              {tenderId && (
                <div className="px-4 lg:px-6 flex items-center gap-2">
                  <Badge variant="outline">Filtered by tender: {tenderId}</Badge>
                  <Link to="/dashboard" className="text-sm text-primary hover:underline">
                    Clear filter
                  </Link>
                </div>
              )}
              <SectionCards bidders={bidders ?? []} />
              <div className="px-4 lg:px-6">
                <ChartAreaInteractive bidders={bidders ?? []} />
              </div>
              <DataTable data={bidders ?? []} />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
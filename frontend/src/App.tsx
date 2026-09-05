import { AppSidebar } from "@/components/app-sidebar"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { SectionCards } from "@/components/section-cards"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

const tableData = [
  {
    id: 1,
    header: "Project Overview",
    type: "Executive Summary",
    status: "Done",
    target: "100",
    limit: "200",
    reviewer: "Eddie Lake",
  },
  {
    id: 2,
    header: "Technical Approach",
    type: "Technical Approach",
    status: "In Progress",
    target: "75",
    limit: "100",
    reviewer: "Jamik Tashpulatov",
  },
  {
    id: 3,
    header: "System Design",
    type: "Design",
    status: "Done",
    target: "90",
    limit: "100",
    reviewer: "Emily Whalen",
  },
  {
    id: 4,
    header: "Project Capabilities",
    type: "Capabilities",
    status: "Not Started",
    target: "50",
    limit: "100",
    reviewer: "Assign reviewer",
  },
]
function App() {
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
              <SectionCards />
              <div className="px-4 lg:px-6">
                <ChartAreaInteractive />
              </div>
              <DataTable data={tableData} />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
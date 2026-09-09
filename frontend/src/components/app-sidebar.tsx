import * as React from "react"
import { Link } from "react-router-dom"

import { NavDocuments } from "@/components/nav-documents"
import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  LayoutDashboardIcon,
  ListIcon,
  ChartBarIcon,
  FolderIcon,
  BellIcon,
  BuildingIcon,
  FileChartColumnIcon,
  ShieldIcon,
  CommandIcon,
} from "lucide-react"

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  navMain: [
    { title: "Tender Workspace", url: "/tenders", icon: <BuildingIcon /> },
    { title: "Bidder Queue", url: "/dashboard", icon: <LayoutDashboardIcon /> },
    { title: "Tender Rule Studio", url: "/rules", icon: <ListIcon /> },
    { title: "Audit Trail", url: "/audit", icon: <ChartBarIcon /> },
    { title: "Debarment Index", url: "/debarment", icon: <FolderIcon /> },
    { title: "Notifications", url: "/notifications", icon: <BellIcon /> },
  ],
  navSecondary: [
    { title: "Admin", url: "/admin", icon: <ShieldIcon /> },
  ],
  documents: [
    { name: "Dossiers", url: "/dossiers", icon: <FileChartColumnIcon /> },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild className="data-[slot=sidebar-menu-button]:p-1.5!">
              <Link to="/dashboard">
                <CommandIcon className="size-5!" />
                <span className="text-base font-semibold">PRAMAAN</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavDocuments items={data.documents} />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  )
}
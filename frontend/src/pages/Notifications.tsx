import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Badge } from "@/components/ui/badge"

type Notification = { id: string; title: string; description: string; severity: string }

export default function Notifications() {
  const { data: notifications, isLoading } = useQuery<Notification[]>({
    queryKey: ["notifications"],
    queryFn: () => apiFetch("/notifications"),
  })

  const severityVariant: Record<string, "destructive" | "outline" | "secondary"> = {
    high: "destructive", medium: "outline", low: "secondary",
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Notifications</h1>
        <p className="text-sm text-muted-foreground mt-1">Pending items awaiting officer or admin action</p>
      </div>
      <div className="space-y-3">
        {isLoading && <p className="text-muted-foreground text-sm">Loading...</p>}
        {notifications?.map((n) => (
          <div key={n.id} className="rounded-lg border p-4 flex items-start justify-between gap-4">
            <div>
              <div className="font-medium">{n.title}</div>
              <div className="text-sm text-muted-foreground">{n.description}</div>
            </div>
            <Badge variant={severityVariant[n.severity]}>{n.severity}</Badge>
          </div>
        ))}
      </div>
    </div>
  )
}
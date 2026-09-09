import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { LinkIcon } from "lucide-react"

type Relationship = { bidderA: string; bidderB: string; sharedAttribute: string; detail: string }

export default function RelationshipGraph() {
  const { data: relationships, isLoading } = useQuery<Relationship[]>({
    queryKey: ["relationships"],
    queryFn: () => apiFetch("/relationships"),
  })

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Bidder Relationship Graph</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Flags bidders that share directors, addresses, or contact details — a common debarment-evasion pattern
        </p>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Loading...</p>}

      {relationships?.length === 0 && (
        <p className="text-muted-foreground text-sm">No shared attributes detected among current bidders.</p>
      )}

      <div className="space-y-3">
        {relationships?.map((r, i) => (
          <div key={i} className="rounded-lg border border-amber-500 bg-amber-50 dark:bg-amber-950/20 p-4 flex items-start gap-3">
            <LinkIcon className="size-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-medium">
                {r.bidderA} ↔ {r.bidderB}
              </div>
              <div className="text-sm text-muted-foreground">
                Shared: <strong>{r.sharedAttribute}</strong> — {r.detail}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type AuditEntry = {
  id: number
  timestamp: string
  actionType: string
  description: string
  ruleVersion: string
  actor: string
  evidenceRef: string
}

export default function AuditTrail() {
  const { data: entries, isLoading } = useQuery<AuditEntry[]>({
    queryKey: ["audit"],
    queryFn: () => apiFetch("/audit"),
  })

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="text-muted-foreground text-sm">
          Immutable, hash-chained record of every verification and officer decision
        </p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Rule Version</TableHead>
            <TableHead>Actor</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                Loading audit log...
              </TableCell>
            </TableRow>
          )}
          {entries?.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="text-sm text-muted-foreground">
                {new Date(entry.timestamp).toLocaleString()}
              </TableCell>
              <TableCell>
                <Badge variant={entry.actionType === "Officer Decision" ? "default" : "secondary"}>
                  {entry.actionType}
                </Badge>
              </TableCell>
              <TableCell>{entry.description}</TableCell>
              <TableCell className="font-mono text-xs">{entry.ruleVersion}</TableCell>
              <TableCell>{entry.actor}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
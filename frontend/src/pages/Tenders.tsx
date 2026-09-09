import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

type Tender = { id: string; name: string; bidderCount: number; activeRules: number; status: string }

export default function Tenders() {
  const { data: tenders, isLoading } = useQuery<Tender[]>({
    queryKey: ["tenders"],
    queryFn: () => apiFetch("/tenders"),
  })

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Tender Workspace</h1>
        <p className="text-sm text-muted-foreground mt-1">All active and draft tenders under evaluation</p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tender</TableHead>
            <TableHead>Bidders</TableHead>
            <TableHead>Active Rules</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow><TableCell colSpan={4} className="text-center text-muted-foreground">Loading tenders...</TableCell></TableRow>
          )}
          {tenders?.map((t) => (
            <TableRow key={t.id}>
              <TableCell className="font-medium">{t.name}</TableCell>
              <TableCell>{t.bidderCount}</TableCell>
              <TableCell>{t.activeRules}</TableCell>
              <TableCell>
                <Badge variant={t.status === "Open" ? "default" : "secondary"}>{t.status}</Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
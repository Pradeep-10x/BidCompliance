import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { apiFetch } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

type Bidder = { id: number; name: string; gstin: string; complianceScore: number; riskLevel: string }

export default function Dossiers() {
  const { data: bidders, isLoading } = useQuery<Bidder[]>({
    queryKey: ["bidders"],
    queryFn: () => apiFetch("/bidders"),
  })

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Compliance Dossiers</h1>
        <p className="text-sm text-muted-foreground mt-1">Per-bidder evidence and finding records for the Tender Committee</p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Bidder</TableHead>
            <TableHead>GSTIN</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Risk</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">Loading...</TableCell></TableRow>
          )}
          {bidders?.map((b) => (
            <TableRow key={b.id}>
              <TableCell className="font-medium">{b.name}</TableCell>
              <TableCell className="font-mono text-xs">{b.gstin}</TableCell>
              <TableCell>{b.complianceScore}</TableCell>
              <TableCell><Badge variant="outline">{b.riskLevel}</Badge></TableCell>
              <TableCell className="text-right">
                <Link to={`/bidders/${b.id}`} className="text-sm text-primary hover:underline">
                  View Dossier
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
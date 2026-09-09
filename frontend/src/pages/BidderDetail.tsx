import { useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { StatusBadge, type FindingStatus } from "@/components/status-badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { ArrowLeftIcon, PrinterIcon, ShieldAlertIcon } from "lucide-react"

type Finding = {
  id: string
  requirement: string
  category: string
  status: string
  source: string
  evidenceRef: string
}

type DebarmentMatch = {
  entityName: string
  sourceList: string
  debarmentStart: string
  debarmentEnd: string
  matchConfidence: number
} | null

export default function BidderDetail() {
  const { bidderId } = useParams()

  const { data: findings, isLoading } = useQuery<Finding[]>({
    queryKey: ["bidder-findings", bidderId],
    queryFn: () => apiFetch(`/bidders/${bidderId}/findings`),
  })

  const { data: debarmentMatch } = useQuery<DebarmentMatch>({
    queryKey: ["bidder-debarment", bidderId],
    queryFn: () => apiFetch(`/bidders/${bidderId}/debarment-check`),
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link to="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeftIcon className="size-4" />
            Back to Bidder Queue
          </Button>
        </Link>
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <PrinterIcon className="size-4" />
          Print Dossier
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-semibold">Bidder Findings</h1>
        <p className="text-muted-foreground text-sm">
          Requirement-level verification results for this bidder
        </p>
      </div>

      {debarmentMatch && (
        <div className="rounded-lg border border-destructive bg-destructive/5 p-4 flex items-start gap-3">
          <ShieldAlertIcon className="size-5 text-destructive shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-destructive">
              Active Debarment Match Found
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              This bidder matches an active entry on the <strong>{debarmentMatch.sourceList}</strong> debarment
              list ({debarmentMatch.debarmentStart} – {debarmentMatch.debarmentEnd}, {debarmentMatch.matchConfidence}%
              confidence). Review before proceeding with qualification.
            </p>
          </div>
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Requirement</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Evidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                Loading findings...
              </TableCell>
            </TableRow>
          )}
          {findings?.map((f) => (
            <TableRow key={f.id}>
              <TableCell className="font-medium">{f.requirement}</TableCell>
              <TableCell className="text-muted-foreground text-xs font-mono">{f.category}</TableCell>
              <TableCell>
                <StatusBadge status={f.status as FindingStatus} />
              </TableCell>
              <TableCell>{f.source}</TableCell>
              <TableCell className="text-muted-foreground text-xs">{f.evidenceRef}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
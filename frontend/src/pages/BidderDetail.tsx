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
import { ArrowLeftIcon } from "lucide-react"

type Finding = {
  id: string
  requirement: string
  category: string
  status: string
  source: string
  evidenceRef: string
}

export default function BidderDetail() {
  const { bidderId } = useParams()

  const { data: findings, isLoading } = useQuery<Finding[]>({
    queryKey: ["bidder-findings", bidderId],
    queryFn: () => apiFetch(`/bidders/${bidderId}/findings`),
  })

  return (
    <div className="p-6 space-y-4">
      <Link to="/dashboard">
        <Button variant="ghost" size="sm">
          <ArrowLeftIcon className="size-4" />
          Back to Bidder Queue
        </Button>
      </Link>

      <div>
        <h1 className="text-2xl font-semibold">Bidder Findings</h1>
        <p className="text-muted-foreground text-sm">
          Requirement-level verification results for this bidder
        </p>
      </div>

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
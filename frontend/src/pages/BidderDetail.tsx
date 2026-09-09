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
import {
  ArrowLeftIcon,
  PrinterIcon,
  ShieldAlertIcon,
  UsersRoundIcon,
} from "lucide-react"

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

type Bidder = {
  id: number
  name: string
  gstin: string
  complianceScore: number
  verificationDepth: number
  riskLevel: string
  status: string
}

type Relationship = {
  bidderA: string
  bidderB: string
  sharedAttribute: string
  detail: string
}

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

  const { data: bidders } = useQuery<Bidder[]>({
    queryKey: ["bidders"],
    queryFn: () => apiFetch("/bidders"),
  })

  const { data: relationships } = useQuery<Relationship[]>({
    queryKey: ["relationships"],
    queryFn: () => apiFetch("/relationships"),
  })

  const currentBidder = bidders?.find(
    (bidder) => bidder.id === Number(bidderId)
  )

  const bidderRelationships =
    currentBidder && relationships
      ? relationships.filter(
          (relationship) =>
            relationship.bidderA.toLowerCase() ===
              currentBidder.name.toLowerCase() ||
            relationship.bidderB.toLowerCase() ===
              currentBidder.name.toLowerCase()
        )
      : []

  const relationship = bidderRelationships[0]

  const breakdown = {
    passed:
      findings?.filter(
        (finding) =>
          finding.status === "PASS" || finding.status === "VERIFIED"
      ).length ?? 0,

    unavailable:
      findings?.filter(
        (finding) => finding.status === "UNAVAILABLE"
      ).length ?? 0,

    review:
      findings?.filter(
        (finding) =>
          finding.status === "REVIEW" ||
          finding.status === "MISMATCH" ||
          finding.status === "UNVERIFIED"
      ).length ?? 0,

    total: findings?.length ?? 0,
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <Link to="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeftIcon className="size-4" />
            Back to Bidder Queue
          </Button>
        </Link>

        <Button
          variant="outline"
          size="sm"
          onClick={() => window.print()}
        >
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

      {/* Compliance Summary */}
      {currentBidder && (
        <div className="rounded-lg border bg-card p-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <div className="text-sm text-muted-foreground">
                Overall Compliance Score
              </div>

              <div className="mt-1 text-2xl font-semibold">
                {currentBidder.complianceScore}%
              </div>
            </div>

            <div>
              <div className="text-sm text-muted-foreground">
                Verification Depth
              </div>

              <div className="mt-1 text-2xl font-semibold">
                {currentBidder.verificationDepth}%
              </div>
            </div>

            <div>
              <div className="text-sm text-muted-foreground">
                Finding Breakdown
              </div>

              <div className="mt-1 text-sm font-medium">
                {breakdown.passed} of {breakdown.total} checks passed
                {breakdown.unavailable > 0 &&
                  `, ${breakdown.unavailable} unavailable`}
                {breakdown.review > 0 &&
                  `, ${breakdown.review} needs review`}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Debarment Warning */}
      {debarmentMatch && (
        <div className="rounded-lg border border-destructive bg-destructive/5 p-4 flex items-start gap-3">
          <ShieldAlertIcon className="size-5 text-destructive shrink-0 mt-0.5" />

          <div>
            <div className="font-medium text-destructive">
              Active Debarment Match Found
            </div>

            <p className="text-sm text-muted-foreground mt-1">
              This bidder matches an active entry on the{" "}
              <strong>{debarmentMatch.sourceList}</strong> debarment list (
              {debarmentMatch.debarmentStart} –{" "}
              {debarmentMatch.debarmentEnd},{" "}
              {debarmentMatch.matchConfidence}% confidence).
              Review before proceeding with qualification.
            </p>
          </div>
        </div>
      )}

      {/* Relationship Warning */}
      {relationship && (
        <div className="rounded-lg border border-amber-500/50 bg-amber-500/5 p-4 flex items-start gap-3">
          <UsersRoundIcon className="size-5 text-amber-600 shrink-0 mt-0.5" />

          <div>
            <div className="font-medium text-amber-700">
              Relationship / Entity Link Detected
            </div>

            <p className="text-sm text-muted-foreground mt-1">
              This bidder shares{" "}
              <strong>{relationship.sharedAttribute}</strong> with{" "}
              <strong>
                {relationship.bidderA.toLowerCase() ===
                currentBidder?.name.toLowerCase()
                  ? relationship.bidderB
                  : relationship.bidderA}
              </strong>
              .
            </p>

            <p className="text-xs text-muted-foreground mt-2">
              {relationship.detail}
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
              <TableCell
                colSpan={5}
                className="text-center text-muted-foreground"
              >
                Loading findings...
              </TableCell>
            </TableRow>
          )}

          {findings?.map((f) => (
            <TableRow key={f.id}>
              <TableCell className="font-medium">
                {f.requirement}
              </TableCell>

              <TableCell className="text-muted-foreground text-xs font-mono">
                {f.category}
              </TableCell>

              <TableCell>
                <StatusBadge status={f.status as FindingStatus} />
              </TableCell>

              <TableCell>{f.source}</TableCell>

              <TableCell className="text-muted-foreground text-xs">
                {f.evidenceRef}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
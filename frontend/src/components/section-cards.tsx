import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  AlertTriangleIcon,
  ClipboardCheckIcon,
  FileCheck2Icon,
  ShieldCheckIcon,
  
} from "lucide-react"

type Bidder = {
  id: number | string
  name: string
  gstin: string
  complianceScore: number
  verificationDepth: number
  riskLevel: string
  status: string
}

export function SectionCards({ bidders =[] }: { bidders: Bidder[] }) {
  const averageCompliance =
    bidders.length > 0
      ? Math.round(
          bidders.reduce((sum, bidder) => sum + bidder.complianceScore, 0) /
            bidders.length
        )
      : 0

  const pendingReview = bidders.filter(
    (bidder) =>
      bidder.status === "ClarificationRequired" ||
      bidder.status === "Conditional"
  ).length

  const highRiskBidders = bidders.filter(
    (bidder) => bidder.riskLevel === "Critical"
  ).length

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      {/* Active Tenders */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Active Tenders</CardDescription>

          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            8
          </CardTitle>

          <CardAction>
            <Badge variant="outline">
              <FileCheck2Icon />
              Active
            </Badge>
          </CardAction>
        </CardHeader>

        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="flex gap-2 font-medium">
            Currently under verification
            <FileCheck2Icon className="size-4" />
          </div>

          <div className="text-muted-foreground">
            Across CPCL procurement activities
          </div>
        </CardFooter>
      </Card>

      {/* Average Compliance */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Avg Compliance Score</CardDescription>

          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {averageCompliance}%
          </CardTitle>

          <CardAction>
            <Badge variant="outline">
              <ShieldCheckIcon />
              {averageCompliance >= 75 ? "Healthy" : "Needs Review"}
            </Badge>
          </CardAction>
        </CardHeader>

        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="flex gap-2 font-medium">
            Across {bidders.length} bidders
            <ShieldCheckIcon className="size-4" />
          </div>

          <div className="text-muted-foreground">
            Based on current verification results
          </div>
        </CardFooter>
      </Card>

      {/* Pending Review */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Pending Review</CardDescription>

          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {pendingReview}
          </CardTitle>

          <CardAction>
            <Badge variant="outline">
              <ClipboardCheckIcon />
              Officer Action
            </Badge>
          </CardAction>
        </CardHeader>

        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="flex gap-2 font-medium">
            Awaiting officer decision
            <ClipboardCheckIcon className="size-4" />
          </div>

          <div className="text-muted-foreground">
            Clarification or conditional review required
          </div>
        </CardFooter>
      </Card>

      {/* High Risk */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>High Risk Bidders</CardDescription>

          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {highRiskBidders}
          </CardTitle>

          <CardAction>
            <Badge variant="destructive">
              <AlertTriangleIcon />
              Critical
            </Badge>
          </CardAction>
        </CardHeader>

        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="flex gap-2 font-medium">
            Immediate attention required
            <AlertTriangleIcon className="size-4" />
          </div>

          <div className="text-muted-foreground">
            Flagged by compliance verification
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
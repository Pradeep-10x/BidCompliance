import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

type Bidder = {
  id: number | string
  name: string
  complianceScore: number
  verificationDepth: number
}

const chartConfig = {
  complianceScore: {
    label: "Compliance Score",
  },
  verificationDepth: {
    label: "Verification Depth",
  },
} satisfies ChartConfig

export function ChartAreaInteractive({
  bidders = [],
}: {
  bidders?: Bidder[]
}) {
  const chartData = bidders.map((bidder) => ({
    name:
      bidder.name.length > 18
        ? `${bidder.name.slice(0, 18)}…`
        : bidder.name,
    complianceScore: bidder.complianceScore,
    verificationDepth: bidder.verificationDepth,
  }))

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Bidder Compliance Overview</CardTitle>

        <CardDescription>
          Compliance score compared with verification depth
        </CardDescription>
      </CardHeader>

      <CardContent>
        <ChartContainer
          config={chartConfig}
          className="h-[300px] w-full"
        >
          <BarChart
            accessibilityLayer
            data={chartData}
            margin={{
              top: 10,
              right: 10,
              left: 0,
              bottom: 10,
            }}
          >
            <CartesianGrid vertical={false} />

            <XAxis
              dataKey="name"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              interval={0}
              angle={-15}
              textAnchor="end"
              height={60}
            />

            <YAxis
              domain={[0, 100]}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />

            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent />}
            />

            <Bar
              dataKey="complianceScore"
              fill="var(--primary)"
              radius={4}
            />

            <Bar
              dataKey="verificationDepth"
              fill="var(--muted-foreground)"
              radius={4}
            />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
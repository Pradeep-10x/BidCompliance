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

// Splits a long name into up to 2 lines, breaking on a space closest to the middle
function wrapName(name: string): string[] {
  if (name.length <= 14) return [name]
  const words = name.split(" ")
  let line1 = ""
  let line2 = ""
  for (const word of words) {
    if ((line1 + " " + word).trim().length <= 14) {
      line1 = (line1 + " " + word).trim()
    } else {
      line2 = (line2 + " " + word).trim()
    }
  }
  return line2 ? [line1, line2] : [line1]
}

// Custom tick renderer — draws each line as a separate horizontal <tspan>, no rotation
function CustomXAxisTick({ x, y, payload }: any) {
  const lines = wrapName(payload.value)
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fontSize={11} fill="var(--muted-foreground)">
        {lines.map((line, i) => (
          <tspan key={i} x={0} dy={i === 0 ? 14 : 14}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  )
}

export function ChartAreaInteractive({
  bidders = [],
}: {
  bidders?: Bidder[]
}) {
  const chartData = bidders.map((bidder) => ({
    name: bidder.name,
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
          className="h-[320px] w-full"
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
              interval={0}
              height={50}
              tick={<CustomXAxisTick />}
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
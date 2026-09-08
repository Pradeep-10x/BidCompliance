import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Button as UiButton } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form as FormProvider,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

type Rule = {
  id: string
  ruleKey: string
  tenderName: string
  requirementType: string
  value: string
  version: string
  status: string
}
type Bidder = {
  id: number
  name: string
  gstin: string
  complianceScore: number
  verificationDepth: number
  riskLevel: string
  status: string
}

type DryRunResult = {
  ruleId: string
  ruleVersion: string
  bidderId: number
  bidderName: string
  requirement: string
  requiredValue: string
  actualValue: string
  result: "PASS" | "FAIL"
  message: string
}
const ruleSchema = z.object({
  tenderName: z.string().min(2, "Required"),
  requirementType: z.string().min(2, "Required"),
  value: z.string().min(1, "Required"),
})

export default function RuleStudio() {
  const [open, setOpen] = useState(false)
const [dryRunOpen, setDryRunOpen] = useState(false)
const [selectedRule, setSelectedRule] = useState<Rule | null>(null)
const [selectedBidderId, setSelectedBidderId] = useState("")
const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null)

const queryClient = useQueryClient()

  const { data: rules, isLoading } = useQuery<Rule[]>({
    queryKey: ["rules"],
    queryFn: () => apiFetch("/rules"),
  })
const { data: bidders } = useQuery<Bidder[]>({
  queryKey: ["bidders"],
  queryFn: () => apiFetch("/bidders"),
})
  const createRule = useMutation({
    mutationFn: (values: z.infer<typeof ruleSchema>) =>
      apiFetch("/rules", {
        method: "POST",
        body: JSON.stringify(values),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] })
      setOpen(false)
      form.reset()
    },
  })

  const createVersion = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/rules/${id}/versions`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] })
    },
  })

  const dryRunRule = useMutation({
  mutationFn: async ({
    ruleId,
    bidderId,
  }: {
    ruleId: string
    bidderId: number
  }) =>
    apiFetch(`/rules/${ruleId}/dry-run`, {
      method: "POST",
      body: JSON.stringify({ bidderId }),
    }),
  onSuccess: (result: DryRunResult) => {
    setDryRunResult(result)
  },
})

  const deleteRule = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/rules/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] })
    },
  })

  const form = useForm<z.infer<typeof ruleSchema>>({
    resolver: zodResolver(ruleSchema),
    defaultValues: {
      tenderName: "",
      requirementType: "",
      value: "",
    },
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Tender Rule Studio</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage versioned tender compliance rules.
          </p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <UiButton>+ New Rule</UiButton>
          </DialogTrigger>

          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Rule</DialogTitle>
            </DialogHeader>

            <FormProvider {...form}>
              <form
                noValidate
                onSubmit={form.handleSubmit((values) =>
                  createRule.mutate(values)
                )}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="tenderName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tender Name</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g. Refinery Equipment Supply"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="requirementType"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Requirement Type</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g. Turnover Threshold"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="value"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Value</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g. ₹50,00,000 or 20%"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <UiButton
                  type="submit"
                  className="w-full"
                  disabled={createRule.isPending}
                >
                  {createRule.isPending ? "Saving..." : "Save Rule"}
                </UiButton>
              </form>
            </FormProvider>
          </DialogContent>
        </Dialog>

        <Dialog open={dryRunOpen} onOpenChange={setDryRunOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Rule Dry-Run Simulator</DialogTitle>
    </DialogHeader>

    {selectedRule && (
      <div className="space-y-5">
        <div className="rounded-lg border p-4 space-y-2">
          <div className="font-medium">
            {selectedRule.tenderName}
          </div>

          <div className="text-sm text-muted-foreground">
            {selectedRule.requirementType}
          </div>

          <div className="text-sm">
            Required Value:{" "}
            <span className="font-medium">
              {selectedRule.value}
            </span>
          </div>

          <div className="text-sm">
            Rule Version:{" "}
            <Badge variant="outline">
              {selectedRule.version}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">
            Select Bidder
          </label>

          <select
            value={selectedBidderId}
            onChange={(event) => {
              setSelectedBidderId(event.target.value)
              setDryRunResult(null)
            }}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="">Select a bidder</option>

            {bidders?.map((bidder) => (
              <option key={bidder.id} value={bidder.id}>
                {bidder.name}
              </option>
            ))}
          </select>
        </div>

        <UiButton
          className="w-full"
          disabled={
            !selectedBidderId ||
            dryRunRule.isPending
          }
          onClick={() => {
            if (!selectedRule || !selectedBidderId) return

            dryRunRule.mutate({
              ruleId: selectedRule.id,
              bidderId: Number(selectedBidderId),
            })
          }}
        >
          {dryRunRule.isPending
            ? "Running Simulation..."
            : "Run Simulation"}
        </UiButton>

        {dryRunResult && (
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                Simulation Result
              </h3>

              <Badge
                variant={
                  dryRunResult.result === "PASS"
                    ? "default"
                    : "destructive"
                }
              >
                {dryRunResult.result}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-muted-foreground">
                  Bidder
                </div>
                <div className="font-medium">
                  {dryRunResult.bidderName}
                </div>
              </div>

              <div>
                <div className="text-muted-foreground">
                  Rule Version
                </div>
                <div className="font-medium">
                  {dryRunResult.ruleVersion}
                </div>
              </div>

              <div>
                <div className="text-muted-foreground">
                  Required
                </div>
                <div className="font-medium">
                  {dryRunResult.requiredValue}
                </div>
              </div>

              <div>
                <div className="text-muted-foreground">
                  Actual
                </div>
                <div className="font-medium">
                  {dryRunResult.actualValue}
                </div>
              </div>
            </div>

            <div className="rounded-md bg-muted p-3 text-sm">
              {dryRunResult.message}
            </div>

            <p className="text-xs text-muted-foreground">
              Simulation only. No bidder decision or compliance
              status has been changed.
            </p>
          </div>
        )}
      </div>
    )}
  </DialogContent>
</Dialog>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tender Name</TableHead>
            <TableHead>Requirement Type</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Version</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell
                colSpan={6}
                className="text-center text-muted-foreground"
              >
                Loading rules...
              </TableCell>
            </TableRow>
          )}

          {!isLoading && rules?.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={6}
                className="text-center text-muted-foreground"
              >
                No rules found.
              </TableCell>
            </TableRow>
          )}

          {rules?.map((rule) => (
            <TableRow key={rule.id}>
              <TableCell>{rule.tenderName}</TableCell>

              <TableCell>{rule.requirementType}</TableCell>

              <TableCell>{rule.value}</TableCell>

              <TableCell>
                <Badge variant="outline">
                  {rule.version}
                </Badge>
              </TableCell>

              <TableCell>
                <Badge
                  variant={
                    rule.status === "Active"
                      ? "default"
                      : rule.status === "Archived"
                        ? "outline"
                        : "secondary"
                  }
                >
                  {rule.status}
                </Badge>
              </TableCell>

              <TableCell className="text-right">
<div className="flex justify-end gap-2">
  <UiButton
    variant="outline"
    size="sm"
    onClick={() => {
      setSelectedRule(rule)
      setSelectedBidderId("")
      setDryRunResult(null)
      setDryRunOpen(true)
    }}
  >
    Dry Run
  </UiButton>

  <UiButton
    variant="outline"
    size="sm"
    onClick={() => createVersion.mutate(rule.id)}
    disabled={createVersion.isPending}
  >
    New Version
  </UiButton>

  <UiButton
    variant="ghost"
    size="sm"
    onClick={() => deleteRule.mutate(rule.id)}
    disabled={deleteRule.isPending}
  >
    Delete
  </UiButton>
</div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
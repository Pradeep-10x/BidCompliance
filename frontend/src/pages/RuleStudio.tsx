import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
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
  tenderName: string
  requirementType: string
  value: string
  status: string
}

const ruleSchema = z.object({
  tenderName: z.string().min(2, "Required"),
  requirementType: z.string().min(2, "Required"),
  value: z.string().min(1, "Required"),
})

export default function RuleStudio() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: rules, isLoading } = useQuery<Rule[]>({
    queryKey: ["rules"],
    queryFn: () => apiFetch("/rules"),
  })

  const createRule = useMutation({
    mutationFn: (values: z.infer<typeof ruleSchema>) =>
      apiFetch("/rules", { method: "POST", body: JSON.stringify(values) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] })
      setOpen(false)
      form.reset()
    },
  })

  const deleteRule = useMutation({
    mutationFn: (id: string) => apiFetch(`/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  })

  const form = useForm<z.infer<typeof ruleSchema>>({
    resolver: zodResolver(ruleSchema),
    defaultValues: { tenderName: "", requirementType: "", value: "" },
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Tender Rule Studio</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>+ New Rule</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Rule</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((values) => createRule.mutate(values))}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="tenderName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tender Name</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. Refinery Equipment Supply" {...field} />
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
                        <Input placeholder="e.g. Turnover Threshold" {...field} />
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
                        <Input placeholder="e.g. ₹50,00,000 or 20%" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" className="w-full" disabled={createRule.isPending}>
                  {createRule.isPending ? "Saving..." : "Save Rule"}
                </Button>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tender Name</TableHead>
            <TableHead>Requirement Type</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                Loading rules...
              </TableCell>
            </TableRow>
          )}
          {rules?.map((rule) => (
            <TableRow key={rule.id}>
              <TableCell>{rule.tenderName}</TableCell>
              <TableCell>{rule.requirementType}</TableCell>
              <TableCell>{rule.value}</TableCell>
              <TableCell>
                <Badge variant={rule.status === "Active" ? "default" : "secondary"}>
                  {rule.status}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteRule.mutate(rule.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
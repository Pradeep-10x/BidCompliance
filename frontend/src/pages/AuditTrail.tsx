import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type AuditEntry = {
  id: number
  timestamp: string
  actionType: string
  description: string
  ruleVersion: string
  actor: string
  evidenceRef: string
  bidderId: string
  bidderName: string
  tenderId: string
  tenderName: string
  eventHash: string
  previousHash: string
  integrityStatus: "VERIFIED" | "INVALID"
}

export default function AuditTrail() {
  const [bidderSearch, setBidderSearch] = useState("")
  const [tenderFilter, setTenderFilter] = useState("all")
  const [actionFilter, setActionFilter] = useState("all")
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null)

  const { data: entries, isLoading, isError } = useQuery<AuditEntry[]>({
    queryKey: ["audit"],
    queryFn: () => apiFetch("/audit"),
  })

  const tenderOptions = useMemo(() => {
    if (!entries) return []

    return Array.from(
      new Map(
        entries.map((entry) => [entry.tenderId, entry.tenderName])
      ).entries()
    )
  }, [entries])

  const filteredEntries = useMemo(() => {
    if (!entries) return []

    const search = bidderSearch.trim().toLowerCase()

    return entries.filter((entry) => {
      const matchesBidder =
        !search ||
        entry.bidderName.toLowerCase().includes(search) ||
        entry.bidderId.toLowerCase().includes(search)

      const matchesTender =
        tenderFilter === "all" || entry.tenderId === tenderFilter

      const matchesAction =
        actionFilter === "all" || entry.actionType === actionFilter

      return matchesBidder && matchesTender && matchesAction
    })
  }, [entries, bidderSearch, tenderFilter, actionFilter])

  const hasFilters =
    bidderSearch.trim() !== "" ||
    tenderFilter !== "all" ||
    actionFilter !== "all"

  const clearFilters = () => {
    setBidderSearch("")
    setTenderFilter("all")
    setActionFilter("all")
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Immutable, hash-chained record of every verification and officer
          decision
        </p>
      </div>

      {/* Filters */}
      <div className="rounded-lg border bg-card p-4">
        <div className="grid gap-4 md:grid-cols-[2fr_1fr_1fr_auto]">
          {/* Bidder search */}
          <div className="space-y-2">
            <label
              htmlFor="bidder-search"
              className="text-sm font-medium"
            >
              Search Bidder
            </label>

            <Input
              id="bidder-search"
              placeholder="Search by bidder name or ID..."
              value={bidderSearch}
              onChange={(event) => setBidderSearch(event.target.value)}
            />
          </div>

          {/* Tender filter */}
          <div className="space-y-2">
            <label
              htmlFor="tender-filter"
              className="text-sm font-medium"
            >
              Tender
            </label>

            <select
              id="tender-filter"
              value={tenderFilter}
              onChange={(event) => setTenderFilter(event.target.value)}
              className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
            >
              <option value="all">All Tenders</option>

              {tenderOptions.map(([tenderId, tenderName]) => (
                <option key={tenderId} value={tenderId}>
                  {tenderName}
                </option>
              ))}
            </select>
          </div>

          {/* Action filter */}
          <div className="space-y-2">
            <label
              htmlFor="action-filter"
              className="text-sm font-medium"
            >
              Action
            </label>

            <select
              id="action-filter"
              value={actionFilter}
              onChange={(event) => setActionFilter(event.target.value)}
              className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
            >
              <option value="all">All Actions</option>
              <option value="Verification">Verification</option>
              <option value="Officer Decision">Officer Decision</option>
            </select>
          </div>

          {/* Clear button */}
          <div className="flex items-end">
            <Button
              variant="outline"
              onClick={clearFilters}
              disabled={!hasFilters}
              className="w-full"
            >
              Clear Filters
            </Button>
          </div>
        </div>
      </div>

      {/* Result count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing{" "}
          <span className="font-medium text-foreground">
            {filteredEntries.length}
          </span>{" "}
          {filteredEntries.length === 1 ? "audit entry" : "audit entries"}
        </p>
      </div>

      {/* Audit table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Bidder</TableHead>
              <TableHead>Tender</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Rule Version</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Evidence</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="h-24 text-center text-muted-foreground"
                >
                  Loading audit log...
                </TableCell>
              </TableRow>
            )}

            {isError && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="h-24 text-center text-destructive"
                >
                  Failed to load audit log.
                </TableCell>
              </TableRow>
            )}

            {!isLoading &&
              !isError &&
              filteredEntries.map((entry) => (
                <TableRow
  key={entry.id}
  className="cursor-pointer hover:bg-muted/50"
  onClick={() => setSelectedEntry(entry)}
>
                  <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                    {new Date(entry.timestamp).toLocaleString()}
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={
                        entry.actionType === "Officer Decision"
                          ? "default"
                          : "secondary"
                      }
                    >
                      {entry.actionType}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium">{entry.bidderName}</div>
                    <div className="text-xs text-muted-foreground">
                      {entry.bidderId}
                    </div>
                  </TableCell>

                  <TableCell>
                    <div className="font-medium">{entry.tenderName}</div>
                    <div className="text-xs text-muted-foreground">
                      {entry.tenderId}
                    </div>
                  </TableCell>

                  <TableCell className="min-w-[260px]">
                    {entry.description}
                  </TableCell>

                  <TableCell className="font-mono text-xs">
                    {entry.ruleVersion}
                  </TableCell>

                  <TableCell>{entry.actor}</TableCell>

                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {entry.evidenceRef}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}

            {!isLoading &&
              !isError &&
              filteredEntries.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="h-24 text-center text-muted-foreground"
                  >
                    No audit entries match the selected filters.
                  </TableCell>
                </TableRow>
              )}
          </TableBody>
        </Table>
      </div>

            {/* Audit Event Details Dialog */}
      <Dialog
        open={selectedEntry !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedEntry(null)
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit Event Details</DialogTitle>
          </DialogHeader>

          {selectedEntry && (
            <div className="space-y-5">
              {/* Event information */}
              <div className="rounded-lg border p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-muted-foreground">
                      Audit Event
                    </div>
                    <div className="font-mono font-medium">
                      #{selectedEntry.id}
                    </div>
                  </div>

                  <Badge
                    variant={
                      selectedEntry.integrityStatus === "VERIFIED"
                        ? "default"
                        : "destructive"
                    }
                  >
                    {selectedEntry.integrityStatus === "VERIFIED"
                      ? "✓ Chain Verified"
                      : "Integrity Check Failed"}
                  </Badge>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Action
                    </div>
                    <div className="font-medium">
                      {selectedEntry.actionType}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground">
                      Actor
                    </div>
                    <div className="font-medium">
                      {selectedEntry.actor}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground">
                      Timestamp
                    </div>
                    <div className="font-medium">
                      {new Date(
                        selectedEntry.timestamp
                      ).toLocaleString()}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground">
                      Rule Version
                    </div>
                    <div className="font-mono font-medium">
                      {selectedEntry.ruleVersion}
                    </div>
                  </div>
                </div>
              </div>

              {/* Bidder and tender */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">
                    Bidder
                  </div>

                  <div className="mt-1 font-medium">
                    {selectedEntry.bidderName}
                  </div>

                  <div className="text-xs text-muted-foreground">
                    ID: {selectedEntry.bidderId}
                  </div>
                </div>

                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">
                    Tender
                  </div>

                  <div className="mt-1 font-medium">
                    {selectedEntry.tenderName}
                  </div>

                  <div className="text-xs text-muted-foreground">
                    ID: {selectedEntry.tenderId}
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">
                  Event Description
                </div>

                <p className="mt-1 text-sm">
                  {selectedEntry.description}
                </p>
              </div>

              {/* Evidence */}
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">
                  Evidence Reference
                </div>

                <Badge
                  variant="outline"
                  className="mt-2 font-mono text-xs"
                >
                  {selectedEntry.evidenceRef}
                </Badge>
              </div>

              {/* Integrity / hash chain */}
              <div className="rounded-lg border p-4 space-y-4">
                <div>
                  <div className="font-medium">
                    Audit Chain Integrity
                  </div>

                  <p className="text-xs text-muted-foreground mt-1">
                    This event is linked to the previous audit event
                    through the audit hash chain.
                  </p>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Event Hash
                    </div>

                    <div className="mt-1 rounded-md bg-muted p-2 font-mono text-xs break-all">
                      {selectedEntry.eventHash}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-muted-foreground">
                      Previous Event Hash
                    </div>

                    <div className="mt-1 rounded-md bg-muted p-2 font-mono text-xs break-all">
                      {selectedEntry.previousHash}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
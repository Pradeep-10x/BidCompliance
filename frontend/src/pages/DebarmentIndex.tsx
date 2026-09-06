import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { SearchIcon } from "lucide-react"

import { apiFetch } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type DebarmentRecord = {
  id: string
  entityName: string
  pan: string
  gstin: string
  sourceList: string
  debarmentStart: string
  debarmentEnd: string
  matchConfidence: number
  status: "Active" | "Expired"
}

export default function DebarmentIndex() {
  const [searchTerm, setSearchTerm] = useState("")
  const [submittedSearch, setSubmittedSearch] = useState("")

  const { data: results = [], isLoading, isFetching } = useQuery<
    DebarmentRecord[]
  >({
    queryKey: ["debarment", submittedSearch],
    queryFn: () =>
      apiFetch(
        `/debarment/search?q=${encodeURIComponent(submittedSearch)}`
      ),
    enabled: submittedSearch.length > 0,
  })

  function handleSearch() {
    setSubmittedSearch(searchTerm.trim())
  }

  function handleClear() {
    setSearchTerm("")
    setSubmittedSearch("")
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Debarment Index
        </h1>
        <p className="text-muted-foreground">
          Search debarment records across government and PSU source lists.
        </p>
      </div>

      <div className="flex w-full max-w-2xl gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />

          <Input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSearch()
              }
            }}
            placeholder="Search by company name, PAN or GSTIN..."
            className="pl-9"
          />
        </div>

        <Button onClick={handleSearch} disabled={!searchTerm.trim()}>
          Search
        </Button>

        {submittedSearch && (
          <Button variant="outline" onClick={handleClear}>
            Clear
          </Button>
        )}
      </div>

      {submittedSearch && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Entity Name</TableHead>
                <TableHead>Source List</TableHead>
                <TableHead>Debarment Period</TableHead>
                <TableHead>Match Confidence</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {isLoading || isFetching ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="h-24 text-center text-muted-foreground"
                  >
                    Searching debarment records...
                  </TableCell>
                </TableRow>
              ) : results.length > 0 ? (
                results.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell>
                      <div className="font-medium">
                        {record.entityName}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        GSTIN: {record.gstin}
                      </div>
                    </TableCell>

                    <TableCell>{record.sourceList}</TableCell>

                    <TableCell>
                      {record.debarmentStart} → {record.debarmentEnd}
                    </TableCell>

                    <TableCell>
                      <Badge variant="secondary">
                        {record.matchConfidence}%
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <Badge
                        variant={
                          record.status === "Active"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {record.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="h-24 text-center text-muted-foreground"
                  >
                    No debarment records found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {!submittedSearch && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <SearchIcon className="mx-auto mb-4 size-8 text-muted-foreground" />

          <h2 className="font-medium">Search the Debarment Index</h2>

          <p className="mt-1 text-sm text-muted-foreground">
            Enter a company name, PAN or GSTIN to check available debarment
            records.
          </p>
        </div>
      )}
    </div>
  )
}
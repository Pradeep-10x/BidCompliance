import type { LucideIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  CheckCircle2Icon,
  XCircleIcon,
  AlertTriangleIcon,
  HelpCircleIcon,
  CloudOffIcon,
  SearchXIcon,
  ClockIcon,
  GitCompareIcon,
  MinusCircleIcon,
} from "lucide-react"

export type FindingStatus =
  | "PASS"
  | "FAIL"
  | "REVIEW"
  | "UNVERIFIED"
  | "UNAVAILABLE"
  | "NOT_FOUND"
  | "EXPIRED"
  | "MISMATCH"
  | "NOT_APPLICABLE"

type StatusConfig = {
  label: string
  icon: LucideIcon
  variant: "default" | "secondary" | "destructive" | "outline"
  className?: string
}

const statusConfig: Record<FindingStatus, StatusConfig> = {
  PASS: { label: "Verified", icon: CheckCircle2Icon, variant: "default", className: "bg-green-600 hover:bg-green-600" },
  FAIL: { label: "Failed", icon: XCircleIcon, variant: "destructive" },
  REVIEW: { label: "Needs Review", icon: AlertTriangleIcon, variant: "outline", className: "border-amber-500 text-amber-600" },
  UNVERIFIED: { label: "Unverified", icon: HelpCircleIcon, variant: "secondary" },
  UNAVAILABLE: { label: "Source Unavailable", icon: CloudOffIcon, variant: "outline", className: "border-slate-400 text-slate-500" },
  NOT_FOUND: { label: "Not Found", icon: SearchXIcon, variant: "outline" },
  EXPIRED: { label: "Expired", icon: ClockIcon, variant: "outline", className: "border-orange-500 text-orange-600" },
  MISMATCH: { label: "Mismatch", icon: GitCompareIcon, variant: "destructive" },
  NOT_APPLICABLE: { label: "Not Applicable", icon: MinusCircleIcon, variant: "secondary", className: "opacity-60" },
}

export function StatusBadge({ status }: { status: FindingStatus }) {
  const config = statusConfig[status]
  const Icon = config.icon
  return (
    <Badge variant={config.variant} className={config.className}>
      <Icon className="size-3.5" />
      {config.label}
    </Badge>
  )
}
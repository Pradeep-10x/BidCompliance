const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "")
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"


let mockRules = [
  {
    id: "1",
    ruleKey: "rule-1",
    tenderName: "Refinery Equipment Supply",
    requirementType: "Turnover Threshold",
    value: "₹50,00,000",
    version: "v1.0",
    status: "Active",
  },
  {
    id: "2",
    ruleKey: "rule-2",
    tenderName: "IT Infrastructure Upgrade",
    requirementType: "MSE Preference",
    value: "20%",
    version: "v1.0",
    status: "Active",
  },
  {
    id: "3",
    ruleKey: "rule-3",
    tenderName: "Pipeline Maintenance",
    requirementType: "Local Content (Class-I)",
    value: "50%",
    version: "v1.0",
    status: "Draft",
  },
]

export function checkDebarment(bidderName: string, gstin: string) {
  return mockDebarment.find(
    (d) =>
      d.status === "Active" &&
      (d.entityName.toLowerCase() === bidderName.toLowerCase() || d.gstin === gstin)
  )
}
const mockBidders = [
  { id: 1, name: "Alton Plastic Pvt Ltd", gstin: "05ABNTY3290P8ZB", complianceScore: 92, verificationDepth: 88, riskLevel: "Low", status: "Recommended", tenderId: "TND-001" },
  { id: 2, name: "MS Corporation", gstin: "05ABNTY3290P8ZC", complianceScore: 61, verificationDepth: 54, riskLevel: "Critical", status: "ClarificationRequired", tenderId: "TND-001" },
  { id: 3, name: "Sunrise Traders", gstin: "05ABNTY3290P8ZD", complianceScore: 78, verificationDepth: 70, riskLevel: "Medium", status: "Conditional", tenderId: "TND-002" },
  { id: 4, name: "Kaveri Engineering Works", gstin: "05ABNTY3290P8ZE", complianceScore: 95, verificationDepth: 91, riskLevel: "Low", status: "Recommended", tenderId: "TND-003" },
  { id: 5, name: "Deccan Industrial Supplies", gstin: "05ABNTY3290P8ZF", complianceScore: 45, verificationDepth: 38, riskLevel: "Critical", status: "Disqualified", tenderId: "TND-003" },
]
const mockTenders = [
  { id: "TND-001", name: "Refinery Equipment Supply", bidderCount: 2, activeRules: 1, status: "Open" },
  { id: "TND-002", name: "IT Infrastructure Upgrade", bidderCount: 1, activeRules: 1, status: "Open" },
  { id: "TND-003", name: "Pipeline Maintenance", bidderCount: 2, activeRules: 1, status: "Draft" },
]

const mockNotifications = [
  { id: "n1", title: "Clarification pending", description: "MS Corporation — awaiting response for 3 days", severity: "high" },
  { id: "n2", title: "Conditional review pending", description: "Sunrise Traders — conditional approval needs officer sign-off", severity: "medium" },
  { id: "n3", title: "Rule draft awaiting activation", description: "Pipeline Maintenance — Local Content rule still in Draft", severity: "low" },
]

const mockUsers = [
  { id: "u1", name: "R. Sharma", email: "officer@example.com", role: "OFFICER", status: "Active" },
  { id: "u2", name: "A. Verma", email: "admin@example.com", role: "ADMIN", status: "Active" },
  { id: "u3", name: "K. Iyer", email: "auditor@example.com", role: "AUDITOR", status: "Active" },
]

const mockRelationships = [
  { bidderA: "MS Corporation", bidderB: "Sunrise Traders", sharedAttribute: "Registered Address", detail: "Both list 10, Veer Nariman Road, Fort" },
]

const mockFindings: Record<number, Array<{
  id: string
  requirement: string
  category: string
  status: string
  source: string
  evidenceRef: string
}>> = {
  1: [
    { id: "f1", requirement: "GST Registration Active", category: "GST_REGISTRATION", status: "PASS", source: "GST Public API", evidenceRef: "ev-gst-001" },
    { id: "f2", requirement: "Udyam/MSME Registration", category: "MSME_REGISTRATION", status: "PASS", source: "OGD Dataset", evidenceRef: "ev-udyam-001" },
    { id: "f3", requirement: "Debarment Check", category: "DEBARMENT", status: "PASS", source: "Federated Index", evidenceRef: "ev-debar-001" },
  ],
  2: [
    { id: "f4", requirement: "GST Registration Active", category: "GST_REGISTRATION", status: "MISMATCH", source: "GST Public API", evidenceRef: "ev-gst-002" },
    { id: "f5", requirement: "PAN Verification", category: "PAN_INCOME_TAX", status: "REVIEW", source: "ITD Mock", evidenceRef: "ev-pan-002" },
    { id: "f6", requirement: "EPFO Compliance", category: "EPFO", status: "UNAVAILABLE", source: "EPFO Portal", evidenceRef: "ev-epfo-002" },
  ],
}

// default fallback for bidders 3-5
function getFindings(bidderId: number) {
  return mockFindings[bidderId] ?? [
    { id: `f-${bidderId}-1`, requirement: "GST Registration Active", category: "GST_REGISTRATION", status: "PASS", source: "GST Public API", evidenceRef: `ev-${bidderId}-1` },
    { id: `f-${bidderId}-2`, requirement: "Local Content Declaration", category: "MII", status: "UNVERIFIED", source: "Self-Declaration", evidenceRef: `ev-${bidderId}-2` },
    { id: `f-${bidderId}-3`, requirement: "OEM Authorization", category: "OEM", status: "NOT_APPLICABLE", source: "N/A", evidenceRef: `ev-${bidderId}-3` },
  ]
}

let mockAuditEntries = [
  {
    id: 1,
    timestamp: "2026-09-05T09:12:00Z",
    actionType: "Verification",
    description: "GSTIN verified — Alton Plastic Pvt Ltd",
    ruleVersion: "v1.2",
    actor: "System",
    evidenceRef: "ev-001",
    bidderId: "1",
    bidderName: "Alton Plastic Pvt Ltd",
    tenderId: "TND-001",
    tenderName: "Refinery Equipment Supply",
    eventHash: "a91f7c2e8d1045b6",
    previousHash: "GENESIS",
    integrityStatus: "VERIFIED",
  },
  {
    id: 2,
    timestamp: "2026-09-05T09:14:00Z",
    actionType: "Verification",
    description: "PAN cross-check failed — MS Corporation",
    ruleVersion: "v1.2",
    actor: "System",
    evidenceRef: "ev-002",
    bidderId: "2",
    bidderName: "MS Corporation",
    tenderId: "TND-001",
    tenderName: "Refinery Equipment Supply",
      eventHash: "b42d91e7c3a85f10",
  previousHash: "a91f7c2e8d1045b6",
  integrityStatus: "VERIFIED",
  },
  {
    id: 3,
    timestamp: "2026-09-05T10:02:00Z",
    actionType: "Officer Decision",
    description: "Clarification requested — MS Corporation",
    ruleVersion: "v1.2",
    actor: "Officer R. Sharma",
    evidenceRef: "ev-002",
    bidderId: "2",
    bidderName: "MS Corporation",
    tenderId: "TND-001",
    tenderName: "Refinery Equipment Supply",
    eventHash: "c73a52f1d8b94e21",
previousHash: "b42d91e7c3a85f10",
integrityStatus: "VERIFIED",
  },
  {
    id: 4,
    timestamp: "2026-09-06T11:30:00Z",
    actionType: "Officer Decision",
    description: "Override applied — turnover mismatch waived",
    ruleVersion: "v1.3",
    actor: "Officer R. Sharma",
    evidenceRef: "ev-004",
    bidderId: "3",
    bidderName: "Sunrise Traders",
    tenderId: "TND-002",
    tenderName: "IT Infrastructure Upgrade",
    eventHash: "d18e64b9a2f73c50",
previousHash: "c73a52f1d8b94e21",
integrityStatus: "VERIFIED",
  },
  {
    id: 5,
    timestamp: "2026-09-06T14:45:00Z",
    actionType: "Verification",
    description: "Debarment check — no match found — Kaveri Engineering Works",
    ruleVersion: "v1.3",
    actor: "System",
    evidenceRef: "ev-005",
    bidderId: "4",
    bidderName: "Kaveri Engineering Works",
    tenderId: "TND-003",
    tenderName: "Pipeline Maintenance",
    eventHash: "e95b27c4f6a81d32",
previousHash: "d18e64b9a2f73c50",
integrityStatus: "VERIFIED",
  },
]

const mockDebarment = [
  {
    id: "1",
    entityName: "Alton Plastic Pvt Ltd",
    pan: "ABCDE1234F",
    gstin: "05ABNTY3290P8ZB",
    sourceList: "CPPP",
    debarmentStart: "2025-01-15",
    debarmentEnd: "2027-01-15",
    matchConfidence: 98,
    status: "Active",
  },
  {
    id: "2",
    entityName: "MS Corporation",
    pan: "FGHIJ5678K",
    gstin: "05ABNTY3290P8ZC",
    sourceList: "GeM",
    debarmentStart: "2024-06-10",
    debarmentEnd: "2026-06-10",
    matchConfidence: 95,
    status: "Expired",
  },
  {
    id: "3",
    entityName: "Sunrise Traders",
    pan: "LMNOP9012Q",
    gstin: "05ABNTY3290P8ZD",
    sourceList: "IOCL",
    debarmentStart: "2026-02-01",
    debarmentEnd: "2028-02-01",
    matchConfidence: 91,
    status: "Active",
  },
  {
    id: "4",
    entityName: "Kaveri Engineering Works",
    pan: "RSTUV3456W",
    gstin: "05ABNTY3290P8ZE",
    sourceList: "CPPP",
    debarmentStart: "2023-03-20",
    debarmentEnd: "2025-03-20",
    matchConfidence: 87,
    status: "Expired",
  },
  {
    id: "5",
    entityName: "Deccan Industrial Supplies",
    pan: "XYZAB7890C",
    gstin: "05ABNTY3290P8ZF",
    sourceList: "BPCL",
    debarmentStart: "2025-09-01",
    debarmentEnd: "2027-09-01",
    matchConfidence: 96,
    status: "Active",
  },
]
// Mock responses, keyed by "METHOD /path"
const mockResponses: Record<string, unknown> = {
  "POST /auth/login": { access_token: "mock-token-123", token_type: "bearer" },
  "GET /auth/me": {
    id: "mock-id",
    email: "officer@example.com",
    full_name: "Test Officer",
    role: "OFFICER",
    is_active: true,
  },

  "GET /bidders/1/findings": mockFindings[1],
  "GET /bidders/2/findings": mockFindings[2],

}

function mockDelay<T>(data: T, ms = 400): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms))
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const method = (options.method || "GET").toUpperCase()

if (USE_MOCK) {
  if (path === "/rules" && method === "GET") {
    return mockDelay(mockRules)
  }

  if (path === "/tenders" && method === "GET") {
  return mockDelay(mockTenders)
}

if (path === "/relationships" && method === "GET") {
  return mockDelay(mockRelationships)
}
if (path.match(/^\/bidders\/\d+\/debarment-check$/) && method === "GET") {
  const bidderId = Number(path.split("/")[2])
  const bidder = mockBidders.find((b) => b.id === bidderId)
  if (!bidder) return mockDelay(null)
  const match = checkDebarment(bidder.name, bidder.gstin)
  return mockDelay(match ?? null)
}
if (path === "/notifications" && method === "GET") {
  return mockDelay(mockNotifications)
}
if (path === "/admin/users" && method === "GET") {
  return mockDelay(mockUsers)
}

  if (path.match(/^\/bidders\/\d+\/findings$/) && method === "GET") {
    const bidderId = Number(path.split("/")[2])
    return mockDelay(getFindings(bidderId))
  }

  if (path.startsWith("/audit") && method === "GET") {
    const url = new URL(`http://localhost${path}`)

    const bidderId = url.searchParams.get("bidderId")
    const tenderId = url.searchParams.get("tenderId")

    let results = [...mockAuditEntries]

    if (bidderId) {
      results = results.filter((entry) => entry.bidderId === bidderId)
    }

    if (tenderId) {
      results = results.filter((entry) => entry.tenderId === tenderId)
    }

    return mockDelay(results)
  }

 if (path.startsWith("/bidders") && method === "GET" && !path.match(/^\/bidders\/\d+/)) {
  const url = new URL(`http://localhost${path}`)
  const tenderId = url.searchParams.get("tenderId")
  const results = tenderId
    ? mockBidders.filter((b) => b.tenderId === tenderId)
    : mockBidders
  return mockDelay(results)
}

if (path === "/officer/decision" && method === "POST") {
  const body = JSON.parse(options.body as string)
  const bidder = mockBidders.find((b) => b.id === body.bidderId)

  if (bidder) {
    const statusMap: Record<string, string> = {
      accept: "Recommended",
      override: "Conditional",
      escalate: "ClarificationRequired",
      disqualify: "Disqualified",
    }
    bidder.status = statusMap[body.action] ?? bidder.status

    const lastEntry = mockAuditEntries[mockAuditEntries.length - 1]
    const newEntry = {
      id: mockAuditEntries.length + 1,
      timestamp: new Date().toISOString(),
      actionType: "Officer Decision",
      description: `${body.action.charAt(0).toUpperCase() + body.action.slice(1)} applied — ${bidder.name}${body.reason ? `: ${body.reason}` : ""}`,
      ruleVersion: "v1.0",
      actor: "Officer (You)",
      evidenceRef: `ev-${bidder.id}-${Date.now()}`,
      bidderId: String(bidder.id),
      bidderName: bidder.name,
      tenderId: bidder.tenderId ?? "N/A",
      tenderName: "—",
      eventHash: Math.random().toString(16).slice(2, 18),
      previousHash: lastEntry?.eventHash ?? "GENESIS",
      integrityStatus: "VERIFIED" as const,
    }
    mockAuditEntries.push(newEntry)
  }

  return mockDelay({ success: true, bidderId: body.bidderId, action: body.action, reason: body.reason })
}

if (path === "/rules" && method === "POST") {
  const body = JSON.parse(options.body as string || "{}")

  const nextRuleNumber =
    mockRules.reduce((max, rule) => {
      const match = rule.ruleKey.match(/^rule-(\d+)$/)
      return Math.max(max, match ? Number(match[1]) : 0)
    }, 0) + 1

  const newRule = {
    id: String(Date.now()),
    ruleKey: `rule-${nextRuleNumber}`,
    tenderName: body.tenderName,
    requirementType: body.requirementType,
    value: body.value,
    version: "v1.0",
    status: "Draft",
  }

  mockRules.push(newRule)

  return mockDelay(newRule)
}

if (path.match(/^\/rules\/[^/]+\/dry-run$/) && method === "POST") {
  const ruleId = path.split("/")[2]
  const body = JSON.parse((options.body as string) || "{}")

  const rule = mockRules.find((item) => item.id === ruleId)

  if (!rule) {
    throw new Error("Rule not found")
  }

  const bidder = mockBidders.find(
    (item) => item.id === Number(body.bidderId)
  )

  if (!bidder) {
    throw new Error("Bidder not found")
  }

  let actualValue = "Not available"
  let passed = false

  if (rule.requirementType === "Turnover Threshold") {
    const turnoverByBidder: Record<number, number> = {
      1: 8200000,
      2: 4200000,
      3: 6500000,
      4: 9500000,
      5: 3000000,
    }

    const actual = turnoverByBidder[bidder.id] ?? 0
    const required = Number(
      rule.value.replace(/[₹,\s]/g, "")
    )

    actualValue = `₹${actual.toLocaleString("en-IN")}`
    passed = actual >= required
  } else if (rule.requirementType === "MSE Preference") {
    const preferenceByBidder: Record<number, number> = {
      1: 25,
      2: 10,
      3: 20,
      4: 30,
      5: 5,
    }

    const actual = preferenceByBidder[bidder.id] ?? 0
    const required = Number(
      rule.value.replace("%", "").trim()
    )

    actualValue = `${actual}%`
    passed = actual >= required
  } else if (
    rule.requirementType === "Local Content (Class-I)"
  ) {
    const localContentByBidder: Record<number, number> = {
      1: 70,
      2: 45,
      3: 55,
      4: 80,
      5: 30,
    }

    const actual = localContentByBidder[bidder.id] ?? 0
    const required = Number(
      rule.value.replace("%", "").trim()
    )

    actualValue = `${actual}%`
    passed = actual >= required
  } else {
    actualValue = "Sample value"
    passed = true
  }

  return mockDelay({
    ruleId: rule.id,
    ruleVersion: rule.version,
    bidderId: bidder.id,
    bidderName: bidder.name,
    requirement: rule.requirementType,
    requiredValue: rule.value,
    actualValue,
    result: passed ? "PASS" : "FAIL",
    message: passed
      ? "The bidder satisfies this rule in the dry-run simulation."
      : "The bidder does not satisfy this rule in the dry-run simulation.",
  })
}

if (path.match(/^\/rules\/[^/]+\/versions$/) && method === "POST") {
  const sourceRuleId = path.split("/")[2]

  const sourceRule = mockRules.find(
    (rule) => rule.id === sourceRuleId
  )

  if (!sourceRule) {
    throw new Error("Rule not found")
  }

  const versions = mockRules.filter(
    (rule) => rule.ruleKey === sourceRule.ruleKey
  )

  const highestVersion = versions.reduce((highest, rule) => {
    const match = rule.version.match(/^v1\.(\d+)$/)
    return Math.max(highest, match ? Number(match[1]) : 0)
  }, 0)

  if (sourceRule.status === "Active") {
    sourceRule.status = "Archived"
  }

  const newRule = {
    id: String(Date.now()),
    ruleKey: sourceRule.ruleKey,
    tenderName: sourceRule.tenderName,
    requirementType: sourceRule.requirementType,
    value: sourceRule.value,
    version: `v1.${highestVersion + 1}`,
    status: "Draft",
  }

  mockRules.push(newRule)

  return mockDelay(newRule)
}

  if (path.startsWith("/rules/") && method === "DELETE") {
    const id = path.split("/")[2]
    mockRules = mockRules.filter((r) => r.id !== id)

    return mockDelay({ success: true })
  }

  if (path.startsWith("/debarment/search") && method === "GET") {
    const url = new URL(`http://localhost${path}`)
    const searchTerm = (url.searchParams.get("q") || "").toLowerCase().trim()

    if (!searchTerm) {
      return mockDelay([])
    }

    const results = mockDebarment.filter(
      (item) =>
        item.entityName.toLowerCase().includes(searchTerm) ||
        item.pan.toLowerCase().includes(searchTerm) ||
        item.gstin.toLowerCase().includes(searchTerm)
    )

    return mockDelay(results)
  }

  const key = `${method} ${path}`

  if (key in mockResponses) {
    return mockDelay(mockResponses[key])
  }

  console.warn(`No mock defined for ${key}, returning empty object`)
  return mockDelay({})
}

  const token = localStorage.getItem("access_token")
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

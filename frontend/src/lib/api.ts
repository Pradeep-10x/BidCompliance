const BASE_URL = "http://127.0.0.1:8000/api/v1"
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

let mockRules = [
  { id: "1", tenderName: "Refinery Equipment Supply", requirementType: "Turnover Threshold", value: "₹50,00,000", status: "Active" },
  { id: "2", tenderName: "IT Infrastructure Upgrade", requirementType: "MSE Preference", value: "20%", status: "Active" },
  { id: "3", tenderName: "Pipeline Maintenance", requirementType: "Local Content (Class-I)", value: "50%", status: "Draft" },
]
const mockBidders = [
  { id: 1, name: "Alton Plastic Pvt Ltd", gstin: "05ABNTY3290P8ZB", complianceScore: 92, verificationDepth: 88, riskLevel: "Low", status: "Recommended" },
  { id: 2, name: "MS Corporation", gstin: "05ABNTY3290P8ZC", complianceScore: 61, verificationDepth: 54, riskLevel: "Critical", status: "ClarificationRequired" },
  { id: 3, name: "Sunrise Traders", gstin: "05ABNTY3290P8ZD", complianceScore: 78, verificationDepth: 70, riskLevel: "Medium", status: "Conditional" },
  { id: 4, name: "Kaveri Engineering Works", gstin: "05ABNTY3290P8ZE", complianceScore: 95, verificationDepth: 91, riskLevel: "Low", status: "Recommended" },
  { id: 5, name: "Deccan Industrial Supplies", gstin: "05ABNTY3290P8ZF", complianceScore: 45, verificationDepth: 38, riskLevel: "Critical", status: "Disqualified" },
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
  "GET /bidders": [
    { id: "1", name: "Alton Plastic Pvt Ltd", gstin: "05ABNTY3290P8ZB", complianceScore: 92, verificationDepth: 88, riskLevel: "Low", status: "Recommended" },
    { id: "2", name: "MS Corporation", gstin: "05ABNTY3290P8ZC", complianceScore: 61, verificationDepth: 54, riskLevel: "Critical", status: "ClarificationRequired" },
    { id: "3", name: "Sunrise Traders", gstin: "05ABNTY3290P8ZD", complianceScore: 78, verificationDepth: 70, riskLevel: "Medium", status: "Conditional" },
  ],
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
  if (path === "/bidders" && method === "GET") {
  return mockDelay(mockBidders)
}
  if (path === "/rules" && method === "POST") {
    const body = JSON.parse(options.body as string)
    const newRule = { id: String(Date.now()), status: "Draft", ...body }
    mockRules = [...mockRules, newRule]
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
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}
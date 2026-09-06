const BASE_URL = "http://127.0.0.1:8000/api/v1"
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

let mockRules = [
  { id: "1", tenderName: "Refinery Equipment Supply", requirementType: "Turnover Threshold", value: "₹50,00,000", status: "Active" },
  { id: "2", tenderName: "IT Infrastructure Upgrade", requirementType: "MSE Preference", value: "20%", status: "Active" },
  { id: "3", tenderName: "Pipeline Maintenance", requirementType: "Local Content (Class-I)", value: "50%", status: "Draft" },
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
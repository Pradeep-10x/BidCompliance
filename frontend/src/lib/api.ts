const BASE_URL = "http://127.0.0.1:8000/api/v1"
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

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
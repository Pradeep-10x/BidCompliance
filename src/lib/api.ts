const BASE_URL = "http://127.0.0.1:8000/api/v1"

export async function apiFetch(path: string, options: RequestInit = {}) {
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
import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { EyeIcon, EyeOffIcon } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function Login() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  const loginMutation = useMutation({
    mutationFn: () =>
      apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token)
      window.location.href = "/dashboard"
    },
  })

  return (
    <div className="flex h-screen items-center justify-center">
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          loginMutation.mutate()
        }}
        className="w-80 space-y-4"
      >
        <h1 className="text-xl font-semibold">Officer Login</h1>
        <div className="space-y-2">
          <Label htmlFor="officer-email">Email</Label>
          <Input
            id="officer-email"
            type="email"
            autoComplete="username"
            placeholder="officer@example.com"
            value={email}
            aria-invalid={loginMutation.isError}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="officer-password">Password</Label>
          <div className="relative">
            <Input
              id="officer-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              className="pr-10"
              value={password}
              aria-invalid={loginMutation.isError}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="absolute right-1 top-1/2 -translate-y-1/2"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              onClick={() => setShowPassword((visible) => !visible)}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </Button>
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? "Logging in..." : "Log in"}
        </Button>
        {loginMutation.isError && (
          <p role="alert" className="text-sm text-destructive">
            {loginMutation.error.message}
          </p>
        )}
      </form>
    </div>
  )
}

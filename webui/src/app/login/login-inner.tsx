"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FileText, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";

export function LoginInner() {
  const { loginWithKeycloak, loginDemo, login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Live validation (mirrors iacgenie SignInPage): validate email + password as
  // the user types, show inline errors under each field, and keep the submit
  // button disabled until both fields are valid. This matches iacgenie's UX so
  // the login behaviour is identical across platforms.
  const isValidEmail = (val: string) => /^[^@\s]+@[^\s@]+\.[^\s@]+$/.test(val);
  const emailInvalid = !!email && !isValidEmail(email);
  const passwordTooShort = password.length > 0 && password.length < 8;

  // Local email/password login (Phase 0.x), mirroring the iacgenie SignInPage:
  //   - email + password form with client-side validation,
  //   - delegates to the auth-context login() hook (POST /api/v1/auth/login),
  //   - on success the context persists tokens and we land on /dashboard,
  //     otherwise login() populates the shared `loginError` for display.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    // login() manages its own loading + error state and persists on success.
    await login(email.trim().toLowerCase(), password);
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 py-12">
      <div className="glass-card w-full p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <FileText className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to analyze your resumes.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className={emailInvalid ? "border-red-300 focus:border-red-500" : ""}
            />
            {emailInvalid && (
              <p className="mt-1.5 text-xs font-semibold text-destructive">Please enter a valid email address</p>
            )}
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              className={passwordTooShort ? "border-red-300 focus:border-red-500" : ""}
            />
            {passwordTooShort && (
              <p className="mt-1.5 text-xs font-semibold text-destructive">Password must be at least 8 characters</p>
            )}
          </div>

          {error && (
            <p className="text-sm text-destructive" data-testid="login-error">
              {error}
            </p>
          )}

          <Button className="w-full" type="submit" disabled={emailInvalid || passwordTooShort}>
            Sign in
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          <Link href="/forgot-password" className="font-medium text-primary hover:underline">Forgot password?</Link>
        </p>

        <div className="relative mt-6">
          <div className="absolute inset-0 mt-2 flex items-center"><div className="w-full border-b border-border" /></div>
          <div className="relative bg-card text-center text-xs text-muted-foreground">or</div>
        </div>

        <Button variant="outline" className="w-full" onClick={() => { loginDemo(); router.push("/dashboard"); }}>
          Try the demo
        </Button>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          New here? <Link href="/signup" className="font-medium text-primary hover:underline">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

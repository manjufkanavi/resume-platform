"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OtpInput } from "@/components/ui/otp-input";
import { useAuth } from "@/contexts/auth-context";
import { authApi } from "@/lib/auth-api";

// Signup page (Phase 0.4).
//
// Local email/password + OTP flow, independent of Keycloak:
//   1. Email + password -> backend stores a bcrypt hash and emails an OTP,
//      returning an OTP token for the verify step.
//   2. Enter the 6-digit code -> backend verifies + completes setup and returns
//      an access token. We persist it via setCredentials() and land on the dashboard.
export function SignupInner() {
  const { loginDemo, setCredentials } = useAuth();
  const router = useRouter();

  type Screen = "form" | "otp";
  const [screen, setScreen] = useState<Screen>("form");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Keep the OTP token out of React state on unmount (it is session-scoped).
  useEffect(() => {
    const key = "resume_signup_otp_token";
    if (token) sessionStorage.setItem(key, token);
    else {
      const stored = sessionStorage.getItem(key);
      if (stored) setToken(stored);
    }
  }, [token]);

  const otp = otpDigits.join("");
  const isOtpReady = otp.length === 6;

  // Live validation (mirrors iacgenie SignUpPage): validate email + confirm
  // password as the user types, show inline errors / helper text under each
  // field, and keep the submit button disabled until both fields are valid.
  const isValidEmail = (val: string) => /^[^@\s]+@[^\s@]+\.[^\s@]+$/.test(val);
  const emailInvalid = !!email && !isValidEmail(email);
  const passwordsMatch = password === confirmPassword;

  // Step 1: submit email + password.
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
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await authApi.signupLocal(email.trim().toLowerCase(), password);
      if (res.status === "otp_sent") {
        setToken(res.token ?? null);
        setScreen("otp");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } catch (err) {
      setError((err as Error).message || "Signup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: verify the OTP -> completes setup and logs in.
  const handleVerify = async () => {
    if (!isOtpReady || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await authApi.verifyOtpLocal(token, otp);
      setCredentials(res.token, {
        keycloak_id: String((res.user as Record<string, unknown>)?.keycloak_id ?? ""),
        username: "",
        email: String((res.user as Record<string, unknown>)?.email ?? email.trim().toLowerCase()),
        name: String((res.user as Record<string, unknown>)?.name ?? ""),
      });
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message || "Verification failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 py-12">
      <div className="glass-card w-full p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <FileText className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">
            {screen === "form" ? "Create your account" : "Verify your email"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {screen === "form"
              ? "Get unlimited resume analyses."
              : `We've sent a 6-digit code to ${email}`}
          </p>
        </div>

        <div className="space-y-3">
          {screen === "form" ? (
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
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  required
                />
              </div>
              <div>
                <Label htmlFor="confirm">Confirm password</Label>
                <Input
                  id="confirm"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  required
                  className={confirmPassword && !passwordsMatch ? "border-red-300 focus:border-red-500" : ""}
                />
                {confirmPassword && !passwordsMatch ? (
                  <p className="mt-1.5 text-xs font-semibold text-destructive">Passwords do not match</p>
                ) : passwordsMatch && confirmPassword ? (
                  <p className="mt-1.5 text-xs font-semibold text-green-600">Passwords match</p>
                ) : null}
              </div>

              {error && (
                <p className="text-sm text-destructive" data-testid="signup-error">
                  {error}
                </p>
              )}

              <Button className="w-full" disabled={isLoading || emailInvalid || !passwordsMatch}>
                {isLoading ? "Creating account…" : "Create an account"}
              </Button>
            </form>
          ) : (
            <div className="space-y-3">
              <OtpInput value={otpDigits} onChange={setOtpDigits} disabled={isLoading} />

              {error && (
                <p className="text-sm text-destructive" data-testid="signup-error">
                  {error}
                </p>
              )}

              <Button className="w-full" onClick={handleVerify} disabled={!isOtpReady || isLoading}>
                {isLoading ? "Verifying…" : "Verify & finish"}
              </Button>

              <button
                type="button"
                onClick={() => setScreen("form")}
                className="flex items-center gap-1.5 w-full text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeftRight className="h-4 w-4 rotate-180">Back to email</ArrowLeftRight>
                Use a different email
              </button>
            </div>
          )}

          <div className="relative">
            <div className="absolute inset-0 mt-2 flex items-center"><div className="w-full border-b border-border" /></div>
            <div className="relative bg-card text-center text-xs text-muted-foreground">or</div>
          </div>

          <Button variant="outline" className="w-full" onClick={() => { loginDemo(); router.push("/dashboard"); }}>
            Try the demo
          </Button>
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Have an account? <Link href="/login" className="font-medium text-primary hover:underline">Log in</Link>
        </p>
      </div>
    </div>
  );
}

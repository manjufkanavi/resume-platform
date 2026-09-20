"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { KeyRound, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OtpInput } from "@/components/ui/otp-input";
import { authApi } from "@/lib/auth-api";

// Forgot-password page (Phase 0.5).
//
// Two steps, single backend contract:
//   1. Email -> /forgot-password returns an OTP token + "otp_sent".
//   2. Enter the 6-digit code AND a new password -> /reset-password atomically
//      verifies the OTP and rotates the credential, returning a login token.
export function ForgotPasswordInner() {
  const router = useRouter();

  type Screen = "email" | "otp";
  const [screen, setScreen] = useState<Screen>("email");
  const [email, setEmail] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const key = "resume_forgot_otp_token";
    if (token) sessionStorage.setItem(key, token);
    else {
      const stored = sessionStorage.getItem(key);
      if (stored) setToken(stored);
    }
  }, [token]);

  const otp = otpDigits.join("");
  const isOtpReady = otp.length === 6;

  // Step 1: request OTP.
  const handleSubmitEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await authApi.forgotPasswordLocal(email.trim().toLowerCase());
      if (res.status === "otp_sent") {
        setToken(res.token ?? null);
        setScreen("otp");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } catch (err) {
      setError((err as Error).message || "Request failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: verify OTP + rotate password (atomic).
  const handleReset = async () => {
    if (!isOtpReady || !token) return;
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await authApi.resetPasswordLocal(token, otp, password);
      router.push("/login");
    } catch (err) {
      setError((err as Error).message || "Reset failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 py-12">
      <div className="glass-card w-full p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <KeyRound className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">
            {screen === "email" ? "Reset your password" : "Enter verification code"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {screen === "email"
              ? "Enter your email and we'll send you a reset code."
              : `We've sent a 6-digit code to ${email}`}
          </p>
        </div>

        <div className="space-y-3">
          {screen === "email" ? (
            <form onSubmit={handleSubmitEmail} className="space-y-3">
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
                />
              </div>

              {error && (
                <p className="text-sm text-destructive" data-testid="forgot-error">
                  {error}
                </p>
              )}

              <Button className="w-full" disabled={isLoading}>
                {isLoading ? "Sending…" : "Send reset code"}
              </Button>

              <button
                type="button"
                onClick={() => router.push("/login")}
                className="w-full text-sm text-muted-foreground hover:text-foreground"
              >
                Remember your password? Log in
              </button>
            </form>
          ) : (
            <div className="space-y-3">
              <OtpInput value={otpDigits} onChange={setOtpDigits} disabled={isLoading} />

              <div>
                <Label htmlFor="new-password">New password</Label>
                <Input
                  id="new-password"
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
                />
              </div>

              {error && (
                <p className="text-sm text-destructive" data-testid="forgot-error">
                  {error}
                </p>
              )}

              <Button className="w-full" onClick={handleReset} disabled={!isOtpReady || isLoading}>
                {isLoading ? "Resetting…" : "Verify & reset password"}
              </Button>

              <button
                type="button"
                onClick={() => setScreen("email")}
                className="flex items-center gap-1.5 w-full text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeftRight className="h-4 w-4 rotate-180">Back to email</ArrowLeftRight>
                Use a different email
              </button>

              <p className="text-center text-xs text-muted-foreground">
                Didn't get the code? <button type="button" onClick={handleSubmitEmail} disabled={isLoading} className="text-primary hover:underline">Resend</button>
              </p>
            </div>
          )}

          <p className="mt-6 text-center text-sm text-muted-foreground">
            New here? <Link href="/signup" className="font-medium text-primary hover:underline">Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

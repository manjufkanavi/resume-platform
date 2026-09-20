"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";

// Dynamic: uses useSearchParams, so it can't be statically prerendered.
export const dynamic = "force-dynamic";

// Keycloak OAuth code-flow callback: after login/signup/forgot-password
// completes, Keycloak redirects here with ?code=... (and state). We redeem the
// code server-side via /api/v1/auth/exchange so the confidential Keycloak client
// secret never reaches the browser. On success we land on the dashboard; on
// failure Keycloak's own error page or /login is shown.
function CallbackInner() {
  const router = useRouter();
  const search = useSearchParams();
  const { completeAuthFlow } = useAuth();

  // Prefer the code Keycloak set; fall back to ?code= for hosted-flow redirects.
  const [code] = useState(() => search.get("code") ?? "");
  const [state, setState] = useState<string | null>(() => search.get("state"));

  useEffect(() => {
    if (!code) return;

    // Verify the state round-trip (CSRF protection). The login/signup buttons
    // set window.__kcState before redirecting; here we compare against it.
    const expected = (window as unknown as { __kcState?: string }).__kcState;
    if (!expected || expected !== state) {
      // Missing/mismatched state → treat as untrusted; fall back to login.
      window.location.href = "/login";
      return;
    }

    let cancelled = false;
    completeAuthFlow(code)
      .then(() => {
        if (!cancelled) router.push("/dashboard");
      })
      .catch(() => {
        if (!cancelled) window.location.href = "/login";
      });

    return () => {
      cancelled = true;
      // Clear the code/state query params so a reload doesn't re-submit.
      if (typeof window !== "undefined" && window.history?.replaceState) {
        const url = new URL(window.location.href);
        url.searchParams.delete("code");
        url.searchParams.delete("state");
        window.history.replaceState({}, "", `${url.pathname}${url.hash}`);
      }
    };
  }, [completeAuthFlow, router, code, state]);

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center px-6">
      <div className="text-center">
        <div className="mx-auto flex h-10 w-10 animate-spin items-center justify-center rounded-xl bg-primary/10">
          <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent" />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">Completing sign-in…</p>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={null}>
      <CallbackInner />
    </Suspense>
  );
}

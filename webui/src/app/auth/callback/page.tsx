"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";

// Dynamic: uses useSearchParams, so it can't be statically prerendered.
export const dynamic = "force-dynamic";

// Minimal Keycloak callback: on a real deployment this exchanges the auth code
// for a token. For the preview we complete with a demo session and continue.
function CallbackInner() {
  const router = useRouter();
  const search = useSearchParams();
  const { loginDemo } = useAuth();
  const [code] = useState(search.get("code") ?? "");

  useEffect(() => {
    // A real impl would POST {code} to /api/v1/auth/exchange. Here we finalize
    // a demo session and land on the dashboard.
    loginDemo();
    const t = setTimeout(() => router.push(code ? "/dashboard" : "/dashboard"), 400);
    return () => clearTimeout(t);
  }, [loginDemo, router, code]);

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

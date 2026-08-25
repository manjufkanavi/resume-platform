"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";

export function LoginInner() {
  const { loginWithKeycloak, loginDemo } = useAuth();
  const router = useRouter();

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

        <div className="space-y-3">
          <Button className="w-full" onClick={loginWithKeycloak}>
            <ShieldCheck className="h-4 w-4" /> Continue with Keycloak
          </Button>
          <div className="relative">
            <div className="absolute inset-0 mt-2 flex items-center"><div className="w-full border-b border-border" /></div>
            <div className="relative bg-card text-center text-xs text-muted-foreground">or</div>
          </div>
          <Button variant="outline" className="w-full" onClick={() => { loginDemo(); router.push("/dashboard"); }}>
            Try the demo
          </Button>
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          New here? <Link href="/signup" className="font-medium text-primary hover:underline">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

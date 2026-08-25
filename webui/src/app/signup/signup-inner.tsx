"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";

export function SignupInner() {
  const { loginWithKeycloak, loginDemo } = useAuth();
  const router = useRouter();
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 py-12">
      <div className="glass-card w-full p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <FileText className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="mt-4 text-2xl font-bold">Create your account</h1>
          <p className="mt-1 text-sm text-muted-foreground">Get unlimited resume analyses.</p>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label htmlFor="fn">First</Label><Input id="fn" placeholder="Alex" /></div>
            <div><Label htmlFor="ln">Last</Label><Input id="ln" placeholder="Chen" /></div>
          </div>
          <div><Label htmlFor="em">Email</Label><Input id="em" type="email" placeholder="you@example.com" /></div>
          <Button className="w-full">Create account</Button>
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

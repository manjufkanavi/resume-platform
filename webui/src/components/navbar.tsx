"use client";

import Link from "next/link";
import { FileText, Menu, UserRoundX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";

export function Navbar() {
  const { isAuthenticated, user, logout, loginDemo } = useAuth();
  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg">
          <FileText className="h-5 w-5 text-primary" />
          <span>Resume Platform</span>
        </Link>
        <div className="hidden items-center gap-6 md:flex">
          <Link href="/" className="text-sm font-medium text-muted-foreground hover:text-primary">
            Home
          </Link>
          <Link href="/templates" className="text-sm font-medium text-muted-foreground hover:text-primary">
            Templates
          </Link>
          {isAuthenticated && (
            <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-primary">
              My Resumes
            </Link>
          )}
        </div>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {user?.name ?? user?.email}
              </span>
              <Button variant="outline" size="sm" onClick={logout}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={loginDemo}>
                <UserRoundX className="h-4 w-4" /> Try Demo
              </Button>
              <Link href="/login">
                <Button size="sm">Log in</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

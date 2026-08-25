"use client";

import Link from "next/link";
import { FileUp, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useList } from "@/lib/use-data";
import { ResumeCard } from "@/components/resume-card";

// Dynamic: reads useAuth() + live data.
export default function DashboardPage() {
  const { token } = useAuth();
  const { data: resumes, loading } = useList(token);

  return (
    <section className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Resumes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {resumes.length} resume{resumes.length === 1 ? "" : "s"} · analyzed with ATS scoring.
          </p>
        </div>
        <Link href="/upload">
          <Button className="gap-2">
            <FileUp className="h-4 w-4" /> Upload new
          </Button>
        </Link>
      </div>

      {loading ? (
        <p className="mt-10 text-sm text-muted-foreground">Loading resumes…</p>
      ) : resumes.length === 0 ? (
        <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border py-16">
          <Inbox className="h-10 w-10 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">No resumes yet.</p>
          <Link href="/upload" className="mt-4">
            <Button size="sm">Upload your first resume</Button>
          </Link>
        </div>
      ) : (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {resumes.map((r) => (
            <ResumeCard key={r.id} item={r} />
          ))}
        </div>
      )}
    </section>
  );
}

import Link from "next/link";
import { FileText, Pencil, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import type { ResumeListItem } from "@/lib/api";

export function ResumeCard({ item }: { item: ResumeListItem }) {
  const score = item.ats_score;
  return (
    <Card className="group flex h-full flex-col overflow-hidden border-glass-card transition hover:shadow-md">
      <CardContent className="flex h-full flex-col gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-4.5 w-4.5 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{item.filename}</p>
              <p className="truncate text-xs text-muted-foreground">{item.job_title ?? "No title set"}</p>
            </div>
          </div>
          <StatusBadge status={item.status} />
        </div>

        {typeof score === "number" && (
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-xs font-bold text-primary-foreground">
              {score}
            </div>
            <div className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">ATS score</span> · ready
            </div>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Updated {new Date(item.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
        </p>

        <div className="mt-auto flex items-center gap-2">
          <Link
            href={`/resume/${item.id}`}
            className="inline-flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary text-xs font-medium text-primary-foreground hover:opacity-90"
          >
            <Pencil className="h-3.5 w-3.5" /> Review
          </Link>
          {item.status === "completed" && (
            <button
              aria-label="Download resume"
              className="flex h-8 w-8 items-center justify-center rounded-lg border hover:bg-muted"
            >
              <FileText className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
          <button
            aria-label="Delete resume"
            className="flex h-8 w-8 items-center justify-center rounded-lg border hover:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4 text-rose-400" />
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

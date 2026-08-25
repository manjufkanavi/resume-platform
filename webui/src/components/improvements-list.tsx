"use client";

import { CheckCircle2 } from "lucide-react";
import type { ResumeImprovement } from "@/lib/api";

export function ImprovementsList({ improvements }: { improvements: ResumeImprovement }) {
  const rewritten = Object.entries(improvements.rewritten_sections ?? {});
  return (
    <div className="space-y-8">
      {rewritten.length > 0 && (
        <section>
          <h3 className="mb-4 text-lg font-semibold">AI-written sections</h3>
          <div className="space-y-4">
            {rewritten.map(([label, text]) => (
              <div key={label} className="rounded-xl border bg-card p-5">
                <p className="mb-2 text-xs font-uppercase tracking-wide font-semibold uppercase text-primary">
                  {label.replace(/_/g, " ")}
                </p>
                <p className="text-sm leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="mb-4 text-lg font-semibold">Suggested improvements</h3>
        <ul className="space-y-2">
          {(improvements.suggestions ?? []).map((s) => (
            <li key={s} className="flex gap-2.5 text-sm">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section>
          <h3 className="mb-3 text-base font-semibold">Keywords to add</h3>
          <div className="flex flex-wrap gap-2">
            {(improvements.keyword_suggestions ?? []).map((k) => (
              <span key={k} className="rounded-full border bg-primary/10 px-2.5 py-1 text-xs text-primary">
                {k}
              </span>
            ))}
          </div>
        </section>
        <section>
          <h3 className="mb-3 text-base font-semibold">Formatting tips</h3>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {(improvements.formatting_tips ?? []).map((t) => (
              <li key={t} className="flex gap-2">
                <span className="text-primary">•</span><span>{t}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {typeof improvements.ats_score_after === "number" && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-emerald-400">Projected score after these changes</p>
            <p className="text-2xl font-bold text-emerald-300">{improvements.ats_score_after}</p>
          </div>
          <CheckCircle2 className="h-8 w-8 text-emerald-400" />
        </div>
      )}
    </div>
  );
}

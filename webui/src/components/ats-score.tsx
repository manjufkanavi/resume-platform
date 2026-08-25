"use client";

import type { ATSScore } from "@/lib/api";

const R = 52;
const C = 2 * Math.PI * R;
const MID = 60;

function scoreColor(s: number) {
  if (s >= 70) return "text-emerald-500";
  if (s >= 50) return "text-amber-500";
  return "text-rose-500";
}
function arcColor(s: number) {
  if (s >= 70) return "#10b981";
  if (s >= 50) return "#f59e0b";
  return "#f43f5e";
}

function Gauge({ score }: { score: number }) {
  const offset = C * (1 - Math.max(0, Math.min(100, score)) / 100);
  return (
    <div className="relative flex h-32 w-32 items-center justify-center">
      <svg viewBox="0 0 120 120" className="h-32 w-32 -rotate-90">
        <circle cx={MID} cy={MID} r={R} fill="none" strokeWidth="10" className="stroke-border" />
        <circle
          cx={MID}
          cy={MID}
          r={R}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          stroke={arcColor(score)}
          strokeDasharray={C}
          strokeDashoffset={offset}
          style={{ transition: "strokeDashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-bold ${scoreColor(score)}`}>{score}</span>
        <span className="text-xs text-muted-foreground">ATS Score</span>
      </div>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  const w = Math.max(4, Math.min(100, value));
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}</span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}

export function ATSGauge({ score }: { score: ATSScore }) {
  const sections = Object.entries(score.section_scores ?? {});
  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
      <div className="flex flex-col items-center gap-6 md:grid md:grid-cols-2 md:gap-8">
        <Gauge score={score.overall} />

        <div className="space-y-4">
          <Bar label="Keyword match" value={score.keywords_match} />
          <Bar label="Formatting" value={score.formatting} />
          <Bar label="Completeness" value={score.completeness} />

          {sections.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {sections.map(([k, v]) => (
                <span key={k} className={`rounded-full border px-2.5 py-1 text-xs font-medium ${scoreColor(v)}`}>
                  {k.replace(/_/g, " ")}: {v}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {score.missing_keywords?.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-sm font-medium">Missing keywords</p>
          <div className="flex flex-wrap gap-2">
            {score.missing_keywords.map((k) => (
              <span key={k} className="rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs text-rose-400">
                {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {score.recommendations?.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium">Recommendations</p>
          <ul className="list-disc list-inside space-y-1 text-xs text-muted-foreground">
            {score.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

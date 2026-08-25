"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, Trash2, Download, FileText, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { useDetail } from "@/lib/use-data";
import { api } from "@/lib/api";
import { ATSGauge } from "@/components/ats-score";
import { ImprovementsList } from "@/components/improvements-list";
import { StatusBadge } from "@/components/status-badge";

type AnyObj = Record<string, any>;

// Thin server wrapper: Next treats a component that `await params` as a server
// component, so it cannot call client hooks. It just resolves `params` and
// delegates to the client UI below (which holds all hooks/state).
export default async function ResumePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ResumeDetailClient id={id} />;
}

function ResumeDetailClient({ id }: { id: string }) {
  const router = useRouter();
  const { token } = useAuth();
  const { data, loading, error, touch } = useDetail(token, id);

  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const ocr: AnyObj = data?.ocr_json ?? {};

  const doRegenerate = async () => {
    if (!token) return;
    setActionMsg("Re-running pipeline (OCR → ATS → improvements)…");
    try {
      await api.regenerate(id, token);
      setActionMsg("Done — results updated.");
    } catch (e) {
      setActionMsg((e as Error).message);
    }
    touch();
  };

  const doDelete = async () => {
    if (!token) return;
    await api.remove(id, token).catch(() => {});
    touch();
    router.push("/dashboard");
  };

  if (loading && !data) {
    return <section className="mx-auto max-w-5xl px-6 py-12"><p className="text-sm text-muted-foreground">Loading resume analysis…</p></section>;
  }

  if (!data) {
    return (
      <section className="mx-auto max-w-3xl px-6 py-12 text-center">
        <p className="text-sm text-rose-400">{error ?? "Resume not found."}</p>
        <Button className="mt-4" onClick={() => router.push("/dashboard")}>Back to dashboard</Button>
      </section>
    );
  }

  const skills: string[] = Array.isArray(ocr.skills) ? ocr.skills : [];
  const experience: Array<AnyObj> = Array.isArray(ocr.experience) ? ocr.experience : [];
  const education: string[] = Array.isArray(ocr.education) ? ocr.education : [];

  return (
    <section className="mx-auto max-w-5xl px-6 py-10">
      <button onClick={() => router.push("/dashboard")} className="mb-6 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to my resumes
      </button>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{data.filename}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <StatusBadge status={data.status} />
              {data.job_title && <span className="text-sm text-muted-foreground">{data.job_title}</span>}
              {data.experience_years && (
                <span className="text-sm text-muted-foreground">· {data.experience_years} yrs exp.</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled title="Download requires a live backend (MinIO)">
            <Download className="h-4 w-4" /> Download
          </Button>
          <Button variant="outline" size="sm" onClick={doDelete} disabled={data.status === "processing"} className="hover:bg-rose-500/10">
            <Trash2 className="h-4 w-4 text-rose-400" /> Delete
          </Button>
          <Button size="sm" onClick={doRegenerate} disabled={data.status === "processing"} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${data.status === "processing" ? "animate-spin" : ""}`} /> Re-run
          </Button>
        </div>
      </div>

      {actionMsg && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border bg-muted p-3 text-sm">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" /><span>{actionMsg}</span>
        </div>
      )}

      {error && data && (
        <p className="mt-3 text-xs text-amber-400">Live backend unreachable — showing demo analysis.</p>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-5">
        {/* Main: analysis */}
        <div className="lg:col-span-3 space-y-8">
          {data.ats_score && <ATSGauge score={data.ats_score} />}

          <section>
            <h3 className="mb-4 text-lg font-semibold">AI-written sections</h3>
            {data.improvements && data.improvements.rewritten_sections && Object.keys(data.improvements.rewritten_sections).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(data.improvements.rewritten_sections).map(([label, text]) => (
                  <div key={label} className="rounded-xl border bg-card p-5">
                    <p className="mb-2 text-xs font-semibold uppercase text-primary">{label.replace(/_/g, " ")}</p>
                    <p className="text-sm leading-relaxed">{text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Re-run the pipeline to generate AI-written sections.</p>
            )}
          </section>

          <section>
            <h3 className="mb-4 text-lg font-semibold">Suggested improvements</h3>
            {data.improvements && data.improvements.suggestions && data.improvements.suggestions.length > 0 ? (
              <ul className="space-y-2">
                {data.improvements.suggestions.map((s) => (
                  <li key={s} className="flex gap-2.5 text-sm"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /><span>{s}</span></li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No suggestions yet.</p>
            )}
          </section>
        </div>

        {/* Side: profile from OCR */}
        <div className="lg:col-span-2 space-y-8">
          <Card>
            <CardHeader><CardTitle className="text-base">Profile extracted</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm">
              {ocr.name && <p className="text-base font-bold">{ocr.name}</p>}
              {ocr.contact && (
                <div className="space-y-1 text-muted-foreground">
                  {ocr.contact.email && <p>Email: {ocr.contact.email}</p>}
                  {ocr.contact.phone && <p>Phone: {ocr.contact.phone}</p>}
                  {ocr.contact.location && <p>Location: {ocr.contact.location}</p>}
                  {ocr.contact.linkedin && <p>LinkedIn: {ocr.contact.linkedin}</p>}
                </div>
              )}
              {ocr.summary && (
                <div><p className="font-medium">Summary</p><p className="mt-1 text-muted-foreground">{ocr.summary}</p></div>
              )}
              {skills.length > 0 && (
                <div><p className="font-medium">Skills</p>
                  <div className="mt-2 flex flex-wrap gap-2">{skills.map((s) => <span key={s} className="rounded-full bg-primary/10 px-2.5 py-1 text-xs text-primary">{s}</span>)}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Experience</CardTitle></CardHeader>
            <CardContent>
              {experience.length > 0 ? (
                <ul className="space-y-4 text-sm">
                  {experience.map((job, i) => (
                    <li key={i} className="relative pl-6 before:absolute before:left-2 before:top-2 before:h-2 before:w-2 before:rounded-full before:bg-primary">
                      <p className="font-medium">{job.role}</p>
                      <p className="text-xs text-muted-foreground">{job.company} · {job.period}</p>
                      {Array.isArray(job.bullets) && (
                        <ul className="mt-1 list-disc list-inside text-muted-foreground">{job.bullets.map((b: string, k: number) => <li key={k}>{b}</li>)}</ul>
                      )}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-sm text-muted-foreground">No experience extracted.</p>}
            </CardContent>
          </Card>

          {education.length > 0 && (
            <Card><CardHeader><CardTitle className="text-base">Education</CardTitle></CardHeader>
              <CardContent><ul className="list-disc list-inside text-sm text-muted-foreground">{education.map((e) => <li key={e}>{e}</li>)}</ul></CardContent></Card>
          )}
        </div>
      </div>
    </section>
  );
}

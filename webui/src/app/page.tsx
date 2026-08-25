import Link from "next/link";
import { FileText, ArrowRight, CheckCircle2, BarChart3, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-hero-gradient">
      {/* Hero */}
      <section className="px-6 pt-20 pb-16 text-center">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            ATS-optimized resumes in minutes
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Land more interviews with a{" "}
            <span className="text-primary">resume that scores</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Upload your resume and get an ATS score, a tailored keyword analysis, and
            AI-written improvements — rebuilt with the same design system as LightSerp.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/upload">
              <Button size="lg" className="gap-2 w-full sm:w-auto">
                Upload your resume
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/templates">
              <Button size="lg" variant="outline" className="gap-2 w-full sm:w-auto">
                Browse templates
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="text-center text-2xl font-bold">How it works</h2>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {[
            { icon: FileText, t: "Upload", d: "Drop a PDF, DOCX, JPG or PNG. We extract structure via OCR." },
            { icon: BarChart3, t: "Get your ATS score", d: "Keyword match, formatting and completeness — broken down." },
            { icon: Sparkles, t: "Improve", d: "AI-written sections and keyword suggestions to boost your fit." },
          ].map(({ icon: Icon, t, d }, i) => (
            <div key={i} className="glass-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{t}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-2">
          {[
            "Single-column ATS-friendly templates",
            "Real-time score breakdown by section",
            "AI rewrite of your summary and bullets",
            "Resume history with per-resume analysis",
          ].map((f) => (
            <div key={f} className="flex items-center gap-3 text-sm">
              <CheckCircle2 className="h-5 w-5 text-primary" />
              <span>{f}</span>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 text-center">
        <div className="mx-auto max-w-2xl">
          <h2 className="text-3xl font-bold">Ready to upgrade your resume?</h2>
          <p className="mt-3 text-muted-foreground">Try the demo — no account required.</p>
          <Link href="/dashboard" className="mt-6 inline-block w-full sm:w-auto">
            <Button size="lg" className="gap-2 w-full">
              Start with demo data
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}

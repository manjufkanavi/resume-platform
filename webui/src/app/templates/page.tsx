import Link from "next/link";
import { FileText, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const templates = [
  { name: "Executive", style: "from-slate-500 to-slate-700", tags: ["One-column", "ATS-friendly"] },
  { name: "Modern", style: "from-primary to-purple-700", tags: ["One-column", "Clean"] },
  { name: "Technical", style: "from-sky-500 to-sky-700", tags: ["One-column", "Skills-first"] },
  { name: "Academic", style: "from-emerald-500 to-emerald-700", tags: ["Publications", "One-column"] },
  { name: "Creative", style: "from-rose-500 to-rose-700", tags: ["Visual", "One-column"] },
  { name: "Minimal", style: "from-zinc-500 to-zinc-700", tags: ["Whitespace", "One-column"] },
];

export default function TemplatesPage() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Resume templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          All templates are single-column and ATS-friendly. Pick one, then upload your content.
        </p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((t) => (
          <Card key={t.name} className="overflow-hidden">
            <div className={`flex h-48 items-end p-4 bg-gradient-to-br ${t.style}`}>
              <FileText className="h-8 w-8 text-white/80" />
            </div>
            <CardContent className="mt-4 flex flex-col gap-3 p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{t.name}</h3>
                <div className="flex gap-1.5">
                  {t.tags.map((g) => (
                    <span key={g} className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">{g}</span>
                  ))}
                </div>
              </div>
              <Link href="/upload" className="mt-auto">
                <Button size="sm" className="w-full gap-2">Use this template</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

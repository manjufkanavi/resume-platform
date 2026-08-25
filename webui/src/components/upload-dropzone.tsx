"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export function UploadDropzone() {
  const router = useRouter();
  const { token } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [years, setYears] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFile = (f: File | null) => {
    if (!f) return;
    const allowed = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "image/png",
      "image/jpeg",
    ];
    if (!allowed.includes(f.type)) {
      setError("Unsupported file. Allowed: PDF, DOCX, JPG, PNG.");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File too large (max 10MB).");
      return;
    }
    setError(null);
    setFile(f);
  };

  const submit = async () => {
    if (!file) {
      setError("Please choose a resume file first.");
      return;
    }
    if (!token) {
      router.push("/login");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const res = await api.upload(token, file, jobTitle, years ? Number(years) : undefined);
      router.push(`/resume/${res.resume_id}`);
    } catch (e) {
      setError((e as Error).message || "Upload failed.");
      setUploading(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-5">
      <div className="lg:col-span-3">
        <h2 className="text-2xl font-bold">Upload your resume</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          PDF, DOCX, JPG or PNG (max 10MB). We extract, score your ATS fit, and suggest improvements.
        </p>

        <button
          onClick={() => fileRef.current?.click()}
          className="mt-6 flex h-52 flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border bg-muted/40 transition hover:border-primary hover:bg-primary/5"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
            <FileUp className="h-6 w-6 text-primary" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium">Click to browse or drop your file here</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {file ? `${file.name} · ${(file.size / 1024).toFixed(0)} KB` : "PDF · DOCX · JPG · PNG"}
            </p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg"
            className="hidden"
            onChange={(e) => onFile(e.target.files?.[0] ?? null)}
          />
        </button>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </div>

      <div className="lg:col-span-2 space-y-4">
        <div>
          <Label htmlFor="job">Target job title (optional)</Label>
          <Input
            id="job"
            placeholder="e.g. Senior Software Engineer"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="years">Years of experience (optional)</Label>
          <Input
            id="years"
            type="number"
            min={0}
            placeholder="e.g. 8"
            value={years}
            onChange={(e) => setYears(e.target.value)}
          />
        </div>
        <div className="rounded-xl border bg-muted/40 p-4 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">What happens next</p>
          <ol className="mt-2 space-y-1.5 list-decimal list-inside">
            <li>OCR extracts your experience, skills and education.</li>
            <li>An ATS score is calculated against your target role.</li>
            <li>AI suggestions show how to improve your fit.</li>
          </ol>
        </div>
        <Button className="w-full" size="lg" onClick={submit} disabled={!file || uploading}>
          {uploading ? "Uploading…" : "Analyze resume"}
        </Button>
      </div>
    </div>
  );
}

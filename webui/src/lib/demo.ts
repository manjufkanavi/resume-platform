// Demo fixtures — used when the backend is unreachable so every page renders fully.
// Structure matches src/lib/api.ts response models.

import type { ResumeListItem, ResumeResult } from "./api";

const statusColors: Record<string, string> = {
  completed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  processing: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  pending: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  failed: "bg-rose-500/15 text-rose-400 border-rose-500/30",
};

function iso(daysAgo: number): string {
  return new Date(Date.now() - daysAgo * 86400000).toISOString();
}

export const demoResumes: ResumeListItem[] = [
  { id: "demo-1", filename: "alex_chen_so_engineering.pdf", status: "completed", job_title: "Senior Software Engineer", created_at: iso(2), ats_score: 81 },
  { id: "demo-2", filename: "priya_sharma_datascientist.pdf", status: "completed", job_title: "Data Scientist", created_at: iso(9), ats_score: 64 },
  { id: "demo-3", filename: "marcus_williams_marketing.docx", status: "processing", job_title: "Marketing Manager", created_at: iso(1) },
  { id: "demo-4", filename: "nina_rodriguez_financial_anyst.pdf", status: "completed", job_title: "Financial Analyst", created_at: iso(21), ats_score: 47 },
  { id: "demo-5", filename: "james_okoro_product_manager.jpg", status: "failed", job_title: "Product Manager", created_at: iso(40) },
];

const detailSamples: Record<string, ResumeResult> = {
  "demo-1": {
    id: "demo-1",
    filename: "alex_chen_so_engineering.pdf",
    status: "completed",
    job_title: "Senior Software Engineer",
    experience_years: 8,
    created_at: iso(2),
    updated_at: iso(2),
    ocr_json: {
      name: "Alex Chen",
      contact: { email: "alex.chen@email.com", phone: "(555) 123-4567", location: "San Francisco, CA", linkedin: "linkedin.com/in/alexcen" },
      summary: "Software engineer with 8 years of experience building scalable web applications.",
      skills: ["TypeScript", "React", "Node.js", "Python", "AWS", "PostgreSQL", "Docker"],
      experience: [
        { role: "Senior Software Engineer", company: "TechCorp", period: "2021 - Present", bullets: ["Led migration of monolith to microservices", "Improved API latency by 40%"] },
        { role: "Software Engineer", company: "StartupXYZ", period: "2017 - 2021", bullets: ["Built customer-facing dashboard"] },
      ],
      education: ["B.S. Computer Science, State University"],
    },
    ats_score: {
      overall: 81,
      keywords_match: 85,
      formatting: 78,
      completeness: 82,
      section_scores: { contact: 95, summary: 70, skills: 90, experience: 80, education: 100 },
      missing_keywords: ["Kubernetes", "CI/CD", "system design"],
      recommendations: ["Add infrastructure keywords from the job description", "Quantify leadership impact with metrics"],
    },
    improvements: {
      rewritten_sections: {
        summary: "Staff-level Software Engineer with 8 years of experience designing and delivering scalable distributed systems, leading cross-functional teams, and reducing infrastructure cost by $1.2M annually.",
      },
      suggestions: ["Quantify each achievement with metrics (%, $, teams)", "Mirror exact keywords from the JD: Kubernetes, CI/CD", "Add a \"Projects\" section for open-source contributions"],
      keyword_suggestions: ["Kubernetes", "CI/CD pipelines", "system design", "incident management"],
      formatting_tips: ["Use a single-column layout for ATS compatibility", "Standard section headings (Experience, Education)", "Save as PDF, avoid tables/graphics"],
      ats_score_after: 88,
    },
  },
  "demo-2": {
    id: "demo-2",
    filename: "priya_sharma_datascientist.pdf",
    status: "completed",
    job_title: "Data Scientist",
    experience_years: 5,
    created_at: iso(9),
    updated_at: iso(9),
    ocr_json: { name: "Priya Sharma", summary: "Data scientist focused on ML models." },
    ats_score: { overall: 64, keywords_match: 58, formatting: 71, completeness: 63, section_scores: { contact: 90, summary: 40, skills: 66, experience: 60, education: 85 }, missing_keywords: ["MLOps", "feature engineering", "A/B testing"], recommendations: ["Expand summary with tools", "Add measurable business impact"] },
    improvements: { rewritten_sections: { summary: "Data Scientist with 5 years of experience shipping production ML models, building feature pipelines, and driving A/B experiments that increased conversion by 18%." }, suggestions: ["Name specific models and frameworks", "Add deployment/MLOps experience", "Include business impact numbers"], keyword_suggestions: ["MLOps", "feature engineering", "A/B testing", "Spark"], formatting_tips: ["Add a technical projects section", "Use action verbs"], ats_score_after: 74 },
  },
  "demo-4": {
    id: "demo-4",
    filename: "nina_rodriguez_financial_anyst.pdf",
    status: "completed",
    job_title: "Financial Analyst",
    experience_years: 4,
    created_at: iso(21),
    updated_at: iso(21),
    ocr_json: { name: "Nina Rodriguez" },
    ats_score: { overall: 47, keywords_match: 40, formatting: 55, completeness: 44, section_scores: { contact: 80, summary: 30, skills: 48, experience: 45, education: 60 }, missing_keywords: ["financial modeling", "Bloomberg terminal", "SQL", "power BI"], recommendations: ["Add hard skills section", "Tailor summary to JD", "Quantify analysis impact"] },
    improvements: { rewritten_sections: { summary: "Detail-oriented Financial Analyst with 4 years of experience building financial models, forecasting, and automating reporting that saved 12 hours per week." }, suggestions: ["Add a dedicated Skills section", "Include specific models/tools", "Quantify time/cost savings"], keyword_suggestions: ["financial modeling", "Bloomberg terminal", "SQL", "power BI"], formatting_tips: ["Use a clean single-column format", "Standardize date formats"], ats_score_after: 61 },
  },
};

export function demoDetail(id: string): ResumeResult {
  return detailSamples[id] ?? {
    id,
    filename: "resume.pdf",
    status: "completed",
    job_title: "",
    created_at: iso(3),
    updated_at: iso(3),
    ocr_json: {},
    ats_score: { overall: 70, keywords_match: 70, formatting: 70, completeness: 70, section_scores: {}, missing_keywords: [], recommendations: [] },
    improvements: null,
  };
}

export { statusColors };

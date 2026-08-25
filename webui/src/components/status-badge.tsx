import { Badge } from "@/components/ui/badge";
import { statusColors } from "@/lib/demo";
import type { ResumeStatus } from "@/lib/api";

const label: Record<ResumeStatus, string> = {
  completed: "Ready",
  processing: "Processing",
  pending: "Pending",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: ResumeStatus }) {
  return (
    <Badge variant="outline" className={`${statusColors[status] ?? ""} border px-2 py-0.5 text-xs`}>
      <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
      {label[status] ?? status}
    </Badge>
  );
}

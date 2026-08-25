import { FileText } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t bg-muted/40">
      <div className="mx-auto max-w-7xl px-6 py-8 text-xs text-muted-foreground">
        <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            <span>Resume Platform &copy; 2026</span>
          </div>
          <div className="flex gap-6">
            <span className="hover:text-foreground cursor-pointer">Privacy</span>
            <span className="hover:text-foreground cursor-pointer">Terms</span>
            <span className="hover:text-foreground cursor-pointer">Help</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

import { UploadDropzone } from "@/components/upload-dropzone";

// Dynamic: reads useAuth() + live data.
export default function UploadPage() {
  return (
    <section className="mx-auto max-w-4xl px-6 py-10">
      <UploadDropzone />
    </section>
  );
}

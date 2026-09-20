"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface OtpInputProps {
  value: string[];
  onChange: (digits: string[]) => void;
  disabled?: boolean;
  error?: boolean;
}

/**
 * Six separate OTP digit fields with auto-advance, backspace-trim and paste.
 * Mirrors iacgenie's OTPInput but trimmed to what resume-platform needs.
 */
export function OtpInput({ value, onChange, disabled = false, error = false }: OtpInputProps) {
  const refs = React.useRef<(HTMLInputElement | null)[]>([]);

  const setValue = (index: number, next: string[]) => {
    onChange(next.map((d) => d.slice(0, 1)));
  };

  const handleChange = (index: number, raw: string) => {
    if (!/^\\d*$/.test(raw)) return; // only digits (caret paste edge case)
    const next = [...value];
    if (raw.length > 1) {
      // Paste: fill this slot and any following empty slots.
      next[index] = raw[0];
      for (let i = 1; i < raw.length && index + i < next.length; i++) {
        if (/\d/.test(raw[i])) next[index + i] = raw[i];
      }
      onChange(next);
      const focusIndex = Math.min(index + raw.length, next.length - 1);
      refs.current[focusIndex]?.focus();
    } else {
      next[index] = raw;
      onChange(next);
      if (raw && index < next.length - 1) refs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      e.preventDefault();
      const next = [...value];
      if (!next[index] && index > 0) {
        next[index - 1] = "";
        onChange(next);
        refs.current[index - 1]?.focus();
      } else {
        next[index] = "";
        onChange(next);
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      refs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < value.length - 1) {
      refs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>, index: number) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "");
    if (!pasted) return;
    e.preventDefault();
    const next = [...value];
    for (let i = 0; i < pasted.length && index + i < next.length; i++) {
      next[index + i] = pasted[i];
    }
    onChange(next);
    refs.current[Math.min(index + pasted.length, next.length - 1)]?.focus();
  };

  return (
    <div className="flex justify-center gap-2" data-testid="otp-input">
      {value.map((digit, index) => (
        <input
          key={index}
          ref={(el) => { refs.current[index] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit || ""}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={(e) => handlePaste(e, index)}
          disabled={disabled}
          aria-label={`OTP digit ${index + 1}`}
          className={cn(
            "h-12 w-11 rounded-md border bg-transparent text-center text-lg font-semibold transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            disabled && "opacity-50 cursor-not-allowed",
            error ? "border-destructive" : "border-input"
          )}
        />
      ))}
    </div>
  );
}

export default OtpInput;

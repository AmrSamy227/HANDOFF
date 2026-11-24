import React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", label, error, helperText, id, ...props }, ref) => {
    const generatedId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={generatedId} className="block text-xs font-semibold text-[var(--foreground)]">
            {label}
          </label>
        )}
        <input
          id={generatedId}
          type={type}
          ref={ref}
          className={cn(
            "w-full rounded-lg bg-[var(--input-bg)] border border-[var(--input-border)] px-3.5 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--subtle-foreground)] shadow-xs",
            "transition-colors duration-150 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600",
            error && "border-rose-500 focus:border-rose-500 focus:ring-rose-500/20",
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-rose-500 mt-1 font-medium">{error}</p>}
        {!error && helperText && <p className="text-xs text-[var(--muted-foreground)] mt-1">{helperText}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

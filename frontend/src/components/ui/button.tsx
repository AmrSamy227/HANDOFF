import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "success" | "brand";
  size?: "sm" | "md" | "lg" | "icon";
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading = false, disabled, children, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-50 disabled:pointer-events-none cursor-pointer";

    const variants = {
      primary: "bg-[var(--btn-primary-bg)] text-[var(--btn-primary-fg)] hover:opacity-90 active:opacity-80 shadow-xs",
      secondary: "bg-[var(--btn-secondary-bg)] text-[var(--btn-secondary-fg)] hover:opacity-90 active:opacity-80 border border-[var(--btn-secondary-border)]",
      outline: "bg-transparent text-[var(--foreground)] hover:bg-[var(--muted)] border border-[var(--border)] shadow-xs",
      ghost: "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)]",
      danger: "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200",
      success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs",
      brand: "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-xs",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs tracking-wide",
      md: "h-10 px-4 text-sm tracking-wide",
      lg: "h-12 px-6 text-base tracking-wide",
      icon: "h-9 w-9 p-0 flex items-center justify-center",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

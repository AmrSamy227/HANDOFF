import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "secondary"
    | "outline"
    | "role-owner"
    | "role-admin"
    | "role-member"
    | "role-client"
    | "status-approved"
    | "status-review"
    | "status-changes"
    | "status-draft";
}

/**
 * Semantic Badge Component.
 * Implements strict WCAG 2.1 AA compliant contrast for status and role pills.
 */
export function Badge({ className, variant = "default", children, ...props }: BadgeProps) {
  const base = "inline-flex items-center justify-center font-medium tracking-tight transition-colors";

  const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
    default: "bg-slate-900 text-white text-xs px-2.5 py-0.5 rounded-full",
    secondary: "bg-slate-100 text-slate-700 border border-slate-200 text-xs px-2.5 py-0.5 rounded-full",
    outline: "border border-slate-300 text-slate-700 text-xs px-2.5 py-0.5 rounded-full",
    // Role Badges
    "role-owner": "bg-blue-600 text-white font-bold text-[10px] px-1.5 py-0.5 rounded tracking-wider uppercase shadow-2xs",
    "role-admin": "bg-slate-800 text-white font-semibold text-[10px] px-1.5 py-0.5 rounded tracking-wider uppercase",
    "role-member": "bg-slate-100 text-slate-700 border border-slate-200 font-medium text-[10px] px-1.5 py-0.5 rounded tracking-wider uppercase",
    "role-client": "bg-purple-50 text-purple-700 border border-purple-200 font-semibold text-[10px] px-1.5 py-0.5 rounded tracking-wider uppercase",
    // Status Badges (WCAG AA Compliant: >= 4.5:1 contrast against light badge surface)
    "status-approved": "bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold text-xs px-2.5 py-0.5 rounded-full",
    "status-review": "bg-amber-50 text-amber-800 border border-amber-200 font-semibold text-xs px-2.5 py-0.5 rounded-full",
    "status-changes": "bg-rose-50 text-rose-800 border border-rose-200 font-semibold text-xs px-2.5 py-0.5 rounded-full",
    "status-draft": "bg-slate-100 text-slate-600 border border-slate-200 font-medium text-xs px-2.5 py-0.5 rounded-full",
  };

  return (
    <span className={cn(base, variants[variant], className)} {...props}>
      {children}
    </span>
  );
}

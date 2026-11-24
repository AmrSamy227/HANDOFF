"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, Shield, Plus, Sparkles, CheckCircle } from "lucide-react";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-neutral-400">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
          <p className="text-xs">Loading workspace session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-8 space-y-8">
      {/* Workspace Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-neutral-800">
        <div>
          <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-1">
            <span>Workspace</span>
            <span>•</span>
            <span className="text-emerald-400 flex items-center">
              <CheckCircle className="h-3 w-3 mr-1" /> Authenticated via HttpOnly Session
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Welcome back, {user.first_name || user.email}
          </h1>
          <p className="text-xs text-neutral-400 mt-1">
            User ID: <code className="font-mono text-neutral-300">{user.id}</code>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button variant="secondary" size="sm">
            <Users className="h-3.5 w-3.5 mr-1.5" />
            Invite Client
          </Button>
          <Button variant="primary" size="sm">
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Project
          </Button>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 space-y-1">
          <p className="text-xs text-neutral-400 font-medium">Active Projects</p>
          <p className="text-2xl font-bold text-white tracking-tight">0</p>
          <p className="text-[11px] text-neutral-500">Ready for Milestone 2</p>
        </Card>

        <Card className="p-4 space-y-1">
          <p className="text-xs text-neutral-400 font-medium">Pending Reviews</p>
          <p className="text-2xl font-bold text-white tracking-tight">0</p>
          <p className="text-[11px] text-neutral-500">Deliverables awaiting review</p>
        </Card>

        <Card className="p-4 space-y-1">
          <p className="text-xs text-neutral-400 font-medium">Connected Clients</p>
          <p className="text-2xl font-bold text-white tracking-tight">0</p>
          <p className="text-[11px] text-neutral-500">Client portal access</p>
        </Card>

        <Card className="p-4 space-y-1">
          <p className="text-xs text-neutral-400 font-medium">Account Security</p>
          <p className="text-xs font-semibold text-emerald-400 flex items-center pt-1.5">
            <Shield className="h-4 w-4 mr-1" /> Cookie JWT Protected
          </p>
          <p className="text-[11px] text-neutral-500">HttpOnly / SameSite Lax</p>
        </Card>
      </div>

      {/* Milestone Roadmap Status Banner */}
      <Card className="p-6 border-neutral-800/80 bg-neutral-900/40">
        <div className="flex items-start space-x-4">
          <div className="p-2.5 rounded-lg bg-neutral-800 text-neutral-200 shrink-0">
            <Sparkles className="h-5 w-5 text-amber-400" />
          </div>
          <div className="space-y-1.5 flex-1">
            <h3 className="text-sm font-semibold text-neutral-100">
              Milestone 1 Complete: Backend Foundation & Authentication
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed max-w-3xl">
              Custom UUID User model, PostgreSQL schema, HttpOnly cookie-based JWT authentication, DRF endpoints, and Next.js shell are fully operational. Ready to implement Workspaces and Projects in Milestone 2.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

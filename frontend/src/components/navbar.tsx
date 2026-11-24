"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { LogOut, Layers, User as UserIcon } from "lucide-react";

export function Navbar() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/[0.06] bg-[#030712]/75 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto flex h-14 items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 text-white flex items-center justify-center font-bold text-xs tracking-tighter shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform">
            HF
          </div>
          <span className="font-semibold text-sm tracking-wider uppercase text-white/90 group-hover:text-white transition-colors">
            HANDOFF
          </span>
        </Link>

        <div className="flex items-center space-x-3">
          {loading ? (
            <div className="h-8 w-20 bg-neutral-800/60 animate-pulse rounded-md" />
          ) : user ? (
            <div className="flex items-center space-x-3">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm" className="text-xs text-slate-300 hover:text-white hover:bg-white/[0.06]">
                  <Layers className="h-3.5 w-3.5 mr-1.5" />
                  Dashboard
                </Button>
              </Link>
              <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
                <UserIcon className="h-3.5 w-3.5 text-blue-400" />
                <span className="font-medium text-slate-200">{user.first_name || user.email}</span>
              </div>
              <Button variant="outline" size="sm" onClick={handleLogout} className="text-xs text-slate-400 hover:text-red-300 border-slate-800 hover:bg-slate-900">
                <LogOut className="h-3.5 w-3.5 mr-1.5" />
                Logout
              </Button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Link href="/login">
                <Button variant="ghost" size="sm" className="text-xs text-slate-300 hover:text-white hover:bg-white/[0.06]">
                  Sign In
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm" className="text-xs bg-white text-slate-950 hover:bg-slate-100 font-medium shadow-sm">
                  Get Started
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

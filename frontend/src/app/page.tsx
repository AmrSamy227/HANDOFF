"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  UploadCloud,
  CheckCircle2,
  ChevronRight
} from "lucide-react";

export default function HomePage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"image" | "video" | "pdf">("image");

  return (
    <div className="flex-1 flex flex-col justify-start items-center text-center relative overflow-hidden bg-[#030712]">
      {/* 1. Deep Midnight Atmospheric Gradients (MindCloud-inspired celestial lighting) */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[850px] pointer-events-none select-none overflow-hidden">
        {/* Core Royal/Cobalt Blue Ambient Halo */}
        <div className="absolute top-[-5%] left-1/2 -translate-x-1/2 w-[1100px] h-[550px] bg-gradient-to-b from-blue-600/45 via-blue-700/30 to-transparent blur-[140px] rounded-full" />
        {/* Secondary Cyan/Electric Rim Light */}
        <div className="absolute top-[28%] left-1/2 -translate-x-1/2 w-[800px] h-[360px] bg-sky-500/25 blur-[100px] rounded-full" />
      </div>

      {/* Atmospheric Horizon Light Bleed (Mindcloud sunrise mist across bottom) */}
      <div className="absolute bottom-0 left-0 right-0 h-[380px] bg-gradient-to-t from-sky-300/20 via-blue-600/10 to-transparent blur-[60px] pointer-events-none" />

      {/* Hero Content Container */}
      <div className="max-w-5xl mx-auto px-4 pt-10 pb-20 sm:pt-16 sm:pb-28 space-y-6 sm:space-y-7 z-10 w-full flex flex-col items-center">
        {/* Social Proof / Announcement Frosted Badge */}
        <div className="inline-flex items-center space-x-2 px-3 py-1 sm:px-3.5 sm:py-1.5 rounded-full border border-white/10 bg-white/[0.04] backdrop-blur-xl text-[11px] sm:text-xs text-slate-300 shadow-sm shadow-blue-500/5 hover:border-white/20 transition-all cursor-default max-w-full">
          <span className="flex h-1.5 w-1.5 sm:h-2 sm:w-2 rounded-full bg-blue-400 animate-pulse shrink-0" />
          <span className="font-medium text-slate-200 truncate">HANDOFF Studio v2.0</span>
          <span className="text-slate-500 shrink-0">•</span>
          <span className="text-slate-400 truncate">Creative Collaboration for Agencies</span>
          <ChevronRight className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-slate-400 shrink-0" />
        </div>

        {/* Hero Title: Razor-Sharp, Confident, Massive Typography */}
        <h1 className="text-[28px] sm:text-5xl md:text-7xl font-bold tracking-tight text-white max-w-4xl mx-auto leading-[1.15] sm:leading-[1.08] text-balance">
          From first draft to<br />
          final approval.
        </h1>

        {/* Crisp Subheadline */}
        <p className="text-sm sm:text-base md:text-lg text-slate-400 max-w-2xl mx-auto font-normal leading-relaxed text-balance px-2">
          A centralized visual review studio where freelancers, agencies, and clients annotate designs, stream video feedback, and lock in sign-offs without communication friction.
        </p>

        {/* MindCloud-Style Interactive Centerpiece: Floating White Creative Action Bar */}
        <div className="w-full max-w-2xl mx-auto pt-2 px-2">
          <div className="p-1.5 sm:p-2.5 rounded-2xl bg-white text-slate-900 shadow-2xl shadow-blue-500/25 border border-white flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3 transition-all">
            <div className="flex items-center pl-2 sm:pl-3 gap-2.5 flex-1 min-w-0 py-1 sm:py-0">
              <UploadCloud className="h-5 w-5 text-blue-600 shrink-0" />
              <input
                type="text"
                readOnly
                placeholder="Drop creative files, Figma links, or video cuts..."
                className="bg-transparent text-xs sm:text-base text-slate-800 placeholder:text-slate-400 outline-none w-full cursor-pointer select-none font-medium truncate"
              />
            </div>
            {user ? (
              <Link href="/dashboard" className="w-full sm:w-auto">
                <Button className="w-full sm:w-auto h-10 sm:h-11 px-5 rounded-xl bg-slate-950 text-white hover:bg-slate-800 font-semibold text-xs sm:text-sm shadow-md transition-all">
                  Open Studio <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </Link>
            ) : (
              <Link href="/register" className="w-full sm:w-auto">
                <Button className="w-full sm:w-auto h-10 sm:h-11 px-5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs sm:text-sm shadow-md shadow-blue-600/30 transition-all">
                  Start Free Review <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 mt-3 text-[11px] sm:text-xs text-slate-400">
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-blue-400 shrink-0" /> No credit card required</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-blue-400 shrink-0" /> Client portals included</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-blue-400 shrink-0" /> Multi-tenant workspaces</span>
          </div>
        </div>

        {/* Hero Visual Showcase: Floating Interactive Review Studio Preview */}
        <div className="w-full max-w-4xl mx-auto pt-6 sm:pt-10">
          <div className="rounded-2xl border border-white/10 bg-[#090d18]/90 backdrop-blur-xl shadow-2xl shadow-blue-950/80 overflow-hidden text-left relative group">
            {/* Studio Header Bar */}
            <div className="px-3 sm:px-4 py-2.5 sm:py-3 border-b border-white/[0.08] bg-slate-950/60 flex items-center justify-between gap-2 overflow-x-auto">
              <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
                <div className="flex space-x-1.5">
                  <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-red-500/80" />
                  <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-yellow-500/80" />
                  <div className="h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full bg-emerald-500/80" />
                </div>
                <div className="h-4 w-px bg-white/10 hidden sm:block" />
                <span className="text-[11px] sm:text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <span className="truncate max-w-[120px] sm:max-w-none">Camp-Hero-Visual-v2.png</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">v2.4</span>
                </span>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <div className="flex bg-slate-900 rounded-lg p-0.5 border border-white/10 text-[10px] sm:text-[11px]">
                  <button
                    onClick={() => setActiveTab("image")}
                    className={`px-2 py-0.5 rounded-md transition-colors ${activeTab === "image" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-white"}`}
                  >
                    Image
                  </button>
                  <button
                    onClick={() => setActiveTab("video")}
                    className={`px-2 py-0.5 rounded-md transition-colors ${activeTab === "video" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-white"}`}
                  >
                    Video
                  </button>
                  <button
                    onClick={() => setActiveTab("pdf")}
                    className={`px-2 py-0.5 rounded-md transition-colors ${activeTab === "pdf" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-white"}`}
                  >
                    PDF
                  </button>
                </div>

                <div className="px-2 sm:px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] sm:text-xs font-medium flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                  <span>Approved</span>
                </div>
              </div>
            </div>

            {/* Studio Canvas Area with Pin Annotation */}
            <div className="p-4 sm:p-10 bg-gradient-to-br from-[#0c1322] via-[#080d1a] to-[#040813] relative min-h-[260px] sm:min-h-[380px] flex items-center justify-center">
              {/* Mockup Asset inside Studio Canvas */}
              <div className="w-full max-w-2xl aspect-[16/9] rounded-xl border border-white/10 bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 p-4 sm:p-6 flex flex-col justify-between relative shadow-xl overflow-hidden">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <span className="text-[9px] sm:text-[10px] font-mono text-blue-400 uppercase tracking-widest">Brand Campaign 2026</span>
                    <h3 className="text-base sm:text-2xl font-bold text-white tracking-tight">The Future of Sound</h3>
                  </div>
                  <span className="text-[10px] sm:text-xs text-slate-400 font-mono">1920 × 1080</span>
                </div>

                {/* Annotation Pin #1 */}
                <div className="absolute top-[38%] left-[25%] sm:left-[45%] group/pin cursor-pointer">
                  <div className="h-6 w-6 sm:h-7 sm:w-7 rounded-full bg-blue-600 text-white font-bold text-[10px] sm:text-xs flex items-center justify-center shadow-lg shadow-blue-500/40 border-2 border-white animate-bounce">
                    1
                  </div>
                  {/* Floating Annotation Comment Card */}
                  <div className="absolute left-7 -top-6 sm:left-9 sm:-top-4 w-52 sm:w-64 p-2.5 sm:p-3 rounded-xl bg-slate-950/95 border border-white/15 backdrop-blur-xl shadow-2xl text-[10px] sm:text-xs space-y-1 sm:space-y-1.5 z-20">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 sm:h-2 sm:w-2 rounded-full bg-emerald-400" />
                        Sarah (Client)
                      </span>
                      <span className="text-[9px] sm:text-[10px] text-slate-500 font-mono">2m ago</span>
                    </div>
                    <p className="text-slate-300 leading-snug">
                      &ldquo;Love the typography! Can we increase headline contrast slightly for mobile readability?&rdquo;
                    </p>
                    <div className="flex items-center gap-1.5 pt-0.5">
                      <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[9px] sm:text-[10px] font-medium">Design Feedback</span>
                      <span className="text-[9px] sm:text-[10px] text-slate-400">Resolved in v2.4 ✓</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-end text-[10px] sm:text-xs text-slate-500 pt-6">
                  <span>3 Comments • 2 Reviewers</span>
                  <span className="text-emerald-400 font-medium">Ready for production export</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

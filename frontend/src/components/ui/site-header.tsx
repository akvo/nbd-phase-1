"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";

interface SiteHeaderProps {
  showActions?: boolean;
}

export function SiteHeader({ showActions = true }: SiteHeaderProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="bg-white border-b border-grey-200 h-16 w-full flex items-center justify-between px-4 sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-2">
        <div
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => (window.location.href = "/")}
        >
          <svg
            className="size-8 text-nbd-primary"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
          <span className="font-extrabold text-lg text-nbd-text-dark tracking-tight">
            Logoipsum
          </span>
        </div>
      </div>

      {showActions ? (
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={() => (window.location.href = "/login")}
          >
            Log in
          </Button>
        </div>
      ) : (
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="bg-white hover:bg-slate-100 p-2 rounded-lg text-nbd-text-dark transition-colors outline-none"
          aria-label="Toggle menu"
        >
          <svg
            className="size-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
      )}
    </header>
  );
}
export default SiteHeader;

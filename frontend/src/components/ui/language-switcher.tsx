"use client";

import React, { useState, useRef, useEffect } from "react";
import { useLocale } from "next-intl";
import { locales, localeNames, localeFlags, Locale } from "@/i18n/config";

export function LanguageSwitcher() {
  const currentLocale = useLocale() as Locale;
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleLocaleChange = (locale: Locale) => {
    // Set cookie and reload page
    const setCookie = () => {
      document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=31536000; SameSite=Lax`;
    };
    setCookie();
    window.location.reload();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 hover:bg-slate-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-nbd-primary/50"
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label="Select language"
      >
        {/* Flag */}
        <img
          src={`https://flagcdn.com/w40/${localeFlags[currentLocale]}.png`}
          alt=""
          className="w-5 h-5 rounded-full object-cover"
        />
        <span className="font-medium">{currentLocale.toUpperCase()}</span>
        {/* Chevron */}
        <svg
          className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-150 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          className="absolute right-0 top-full mt-2 w-40 bg-white rounded-xl border border-slate-200 shadow-xl py-1.5 z-50 animate-fade-in"
          role="menu"
        >
          {locales.map((locale) => (
            <button
              key={locale}
              onClick={() => handleLocaleChange(locale)}
              className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors ${
                locale === currentLocale
                  ? "bg-slate-100 text-slate-900 font-medium"
                  : "text-slate-700 hover:bg-slate-50"
              }`}
              role="menuitem"
            >
              <img
                src={`https://flagcdn.com/w40/${localeFlags[locale]}.png`}
                alt=""
                className="w-5 h-5 rounded-full object-cover"
              />
              {localeNames[locale]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LanguageSwitcher;

"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Script from "next/script";
import { useTranslations } from "next-intl";
import { MessageNote } from "@/components/ui/message-note";
import { SiteHeader } from "@/components/ui/site-header";
import { apiClient } from "@/lib/api";

function LoginContent() {
  const t = useTranslations("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const buttonRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/admin/data";

  const handleCredentialResponse = async (response: { credential: string }) => {
    setError(null);
    setLoading(true);

    try {
      const res = await apiClient.post("/auth/google", {
        token: response.credential,
      });

      if (res.status === 200) {
        window.location.href = redirectUrl;
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      const detail = err.response?.data?.detail || "auth_failed";
      setError(detail);
      setLoading(false);
    }
  };

  const initializeGoogleSignIn = () => {
    if (window.google && buttonRef.current) {
      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
        callback: handleCredentialResponse,
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        text: "signin_with",
        shape: "rectangular",
        width: 280,
      });
    }
  };

  useEffect(() => {
    // Initialize if Google script is already loaded
    if (window.google) {
      initializeGoogleSignIn();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-white flex flex-col justify-between font-sans">
      {/* Google Identity Services Script */}
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initializeGoogleSignIn}
      />

      {/* Header Navigation */}
      <SiteHeader showActions={false} />

      {/* Main Login Form Container */}
      <main className="flex-1 flex flex-col justify-center items-center px-4 py-8">
        <div className="w-full max-w-[375px] space-y-8">
          {/* Header Title */}
          <div className="text-center space-y-2">
            <h1 className="text-[22px] font-semibold text-gray-900 tracking-tight">
              {t("title")}
            </h1>
            <p className="text-sm text-gray-500">{t("subtitle")}</p>
          </div>

          {/* Alert Notification */}
          {error && (
            <MessageNote type="error" title={t("errorTitle")}>
              {error === "not_registered"
                ? t("errorNotRegistered")
                : error === "inactive"
                  ? t("errorInactive")
                  : t("errorAuthFailed")}
            </MessageNote>
          )}

          {/* Google Sign-in Section */}
          <div className="space-y-6">
            <div className="flex flex-col items-center space-y-4">
              {loading ? (
                <div className="h-10 flex items-center justify-center text-sm text-slate-500">
                  {t("signingIn")}
                </div>
              ) : (
                <div ref={buttonRef} className="flex justify-center" />
              )}
            </div>
          </div>

          {/* Footer Notice */}
          <div className="text-center pt-4">
            <p className="text-[13px] text-gray-400 leading-relaxed">
              {t("noAccount")}
              <br />
              {t("noSelfRegistration")}
            </p>
          </div>
        </div>
      </main>

      {/* Empty Footer spacing wrapper */}
      <footer className="h-6"></footer>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-white flex items-center justify-center">
          <div className="text-sm text-slate-500">Loading...</div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}

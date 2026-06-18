"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Script from "next/script";
import { MessageNote } from "@/components/ui/message-note";
import { SiteHeader } from "@/components/ui/site-header";
import { apiClient } from "@/lib/api";

const ERROR_MESSAGES: Record<string, string> = {
  not_registered:
    "Your email is not registered. Contact your platform administrator to request access.",
  inactive:
    "Your account has been deactivated. Contact your platform administrator.",
  auth_failed: "Authentication failed. Please try again.",
};

function LoginContent() {
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
    } catch (err: any) {
      const detail = err.response?.data?.detail || "auth_failed";
      setError(ERROR_MESSAGES[detail] || ERROR_MESSAGES.auth_failed);
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
              Log in to your account
            </h1>
            <p className="text-sm text-gray-500">
              Citizen-Led Wetland Monitoring Platform
            </p>
          </div>

          {/* Alert Notification */}
          {error && (
            <MessageNote type="error" title="Sign-in Failed">
              {error}
            </MessageNote>
          )}

          {/* Google Sign-in Section */}
          <div className="space-y-6">
            <div className="flex flex-col items-center space-y-4">
              {loading ? (
                <div className="h-10 flex items-center justify-center text-sm text-slate-500">
                  Signing in...
                </div>
              ) : (
                <div ref={buttonRef} className="flex justify-center" />
              )}
            </div>
          </div>

          {/* Footer Notice */}
          <div className="text-center pt-4">
            <p className="text-[13px] text-gray-400 leading-relaxed">
              No account? Contact your platform administrator.
              <br />
              Self-registration is not available.
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

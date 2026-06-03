"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { MessageNote } from "@/components/ui/message-note";

import { GoogleSignInButton } from "@/components/ui/google-signin-button";
import { SiteHeader } from "@/components/ui/site-header";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    // Mock Login trigger
    alert(`Signing in with: ${email} (Remember me: ${rememberMe})`);
  };

  const handleGoogleLogin = () => {
    alert("Sign in with Google triggered");
  };

  return (
    <div className="min-h-screen bg-white flex flex-col justify-between font-sans">
      {/* Header Navigation */}
      <SiteHeader showActions={false} />

      {/* Main Login Form Container */}
      <main className="flex-1 flex flex-col justify-center items-center px-4 py-8">
        <div className="w-full max-w-[375px] space-y-8">
          {/* Header Title */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-nbd-text-dark tracking-tight">
              Log in to your account
            </h2>
            <p className="text-sm text-grey-500">
              Citizen-Led Wetland Monitoring Platform
            </p>
          </div>

          {/* Alert Notification */}
          {error && (
            <MessageNote type="error" title="Validation Failure">
              {error}
            </MessageNote>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
              <div>
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-nbd-disabled border-transparent focus-visible:border-nbd-primary"
                />
              </div>

              <div>
                <Input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-nbd-disabled border-transparent focus-visible:border-nbd-primary"
                />
              </div>
            </div>

            {/* Remember me & Forgot password */}
            <div className="flex items-center justify-between text-sm">
              <Checkbox
                checked={rememberMe}
                onChange={setRememberMe}
                label="Remember me"
              />
              <a
                href="#forgot"
                className="font-semibold text-nbd-primary hover:text-nbd-primary-hover transition-colors"
                onClick={(e) => {
                  e.preventDefault();
                  alert("Forgot password clicked");
                }}
              >
                Forgot password
              </a>
            </div>

            {/* Actions */}
            <div className="space-y-4 pt-2">
              <Button
                type="submit"
                variant="primary"
                className="w-full h-12 rounded-lg font-semibold"
              >
                Sign in
              </Button>

              {/* Google Sign-in button */}
              <div className="flex justify-center w-full">
                <GoogleSignInButton onClick={handleGoogleLogin} />
              </div>
            </div>
          </form>

          {/* Footer Notice */}
          <div className="text-center pt-4">
            <p className="text-sm text-grey-400 leading-relaxed">
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

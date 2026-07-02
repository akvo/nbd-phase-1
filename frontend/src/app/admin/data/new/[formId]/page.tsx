"use client";

import React, { useState, useEffect, use } from "react";
import { apiClient, adminApiClient } from "@/lib/api";
import { ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import L from "leaflet";
// Dynamically import Webform from akvo-react-form to prevent SSR issues
import dynamic from "next/dynamic";
import { initReactCompat, useAntdStyleCleanup } from "@/lib/react-compat";

initReactCompat(L);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Webform = dynamic<any>(
  () => import("akvo-react-form").then((mod) => mod.Webform),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center space-x-2 text-slate-500 py-4">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading webform...</span>
      </div>
    ),
  }
);

interface NewFormPageProps {
  params: Promise<{
    formId: string;
  }>;
}

export default function NewFormPage({ params }: NewFormPageProps) {
  useAntdStyleCleanup();
  const { formId } = use(params);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [blueprint, setBlueprint] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiClient
      .get(`/forms/${formId}/blueprint`)
      .then((res) => {
        if (active) {
          setBlueprint(res.data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(
            err.response?.data?.detail || "Failed to fetch form blueprint"
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [formId]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleFinish = async (values: any) => {
    setSubmitting(true);
    setError(null);
    try {
      const formType = blueprint?.type;
      const numericFormId = parseInt(formId, 10) || blueprint?.form_id || 1;

      let endpoint = "/submissions/fgd";
      let client = adminApiClient;

      if (formId === "fgd" || formType === 3) {
        endpoint = "/submissions/fgd";
        client = adminApiClient;
      } else if (formId === "lab-qa" || formType === 4) {
        endpoint = "/submissions/lab-qa";
        client = adminApiClient;
      } else {
        endpoint = "/internal/submit";
        client = apiClient;
      }

      const payload = {
        ...values,
        form_id: numericFormId,
      };

      await client.post(endpoint, payload);
      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/admin/data";
      }, 1500);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Failed to submit data. Please check your inputs."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
        <p className="text-slate-500 text-sm">
          Fetching form blueprint definition...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full my-6">
      {/* Back Button */}
      <div className="flex items-center justify-between mb-6">
        <a
          href="/admin/data"
          className="inline-flex items-center space-x-2 text-sm text-slate-500 hover:text-slate-800 transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          <span>Back to Data Overview</span>
        </a>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-lg flex items-start space-x-3 text-red-700 text-sm animate-shake">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-4 text-center">
            <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-500 border border-emerald-100">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">
              Submission Successful!
            </h2>
            <p className="text-slate-500 text-sm max-w-sm">
              Your data has been successfully ingested. Redirecting you back to
              the data overview...
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {blueprint ? (
              <div className="prose prose-slate max-w-none">
                <Webform
                  key={formId}
                  forms={blueprint}
                  onFinish={handleFinish}
                />
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-200 rounded-xl">
                <p className="text-slate-400 text-sm">
                  No blueprint definition was loaded.
                </p>
              </div>
            )}

            {submitting && (
              <div className="fixed inset-0 bg-slate-900/25 backdrop-blur-sm flex items-center justify-center z-50">
                <div className="bg-white rounded-xl p-6 shadow-lg border border-slate-100 flex items-center space-x-4 max-w-xs">
                  <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
                  <span className="text-sm font-medium text-slate-700">
                    Submitting response...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ArrowLeft, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api";
import { initReactCompat, useDynamicStylesheet } from "@/lib/react-compat";

initReactCompat();

// Dynamic import with no SSR
const WebformEditor = dynamic(() => import("akvo-react-form-editor"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-96">
      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
    </div>
  ),
});

// Valid types: input, number, cascade, text, date, option, multiple_option, tree, geo, table, autofield
const ALLOWED_QUESTION_TYPES = [
  "input",
  "number",
  "text",
  "date",
  "option",
  "multiple_option",
  "cascade",
  "geo",
];

export default function FormEditPage() {
  useDynamicStylesheet("/akvo-react-form-editor.css");
  const params = useParams();

  const router = useRouter();
  const formId = params.formId as string;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [formData, setFormData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchForm = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/forms/${formId}/blueprint`);
      setFormData(res.data);
      // Add a short timeout (150ms) to ensure CSS and DOM are fully loaded/settled
      await new Promise((resolve) => setTimeout(resolve, 150));
    } catch (err) {
      console.error("Failed to fetch form:", err);
      setError("Failed to load form. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [formId]);

  useEffect(() => {
    if (formId) {
      fetchForm();
    }
  }, [formId, fetchForm]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      await apiClient.put(`/forms/${formId}`, values);
      router.push("/admin/resources/forms");
    } catch (err) {
      console.error("Failed to save form:", err);
      setError("Failed to save form. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    router.push("/admin/resources/forms");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  if (error && !formData) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error}</p>
          <button
            type="button"
            onClick={fetchForm}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            type="button"
            onClick={handleBack}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              Edit Form: {formData?.name}
            </h2>
            <p className="text-slate-500 text-sm mt-0.5">
              Form ID: {formId} • Version: {formData?.version || "Draft"}
            </p>
          </div>
        </div>
        {saving && (
          <div className="flex items-center space-x-2 text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Saving...</span>
          </div>
        )}
      </div>

      {/* Editor - isolated styles */}
      <div
        className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm min-h-[600px]"
        style={{ isolation: "isolate" }}
      >
        {formData && (formData.form_id || formData.id) && (
          <div className="arfe-editor-wrapper">
            <WebformEditor
              key={formData.form_id || formData.id || formId}
              initialValue={formData}
              onSave={handleSave}
              limitQuestionType={ALLOWED_QUESTION_TYPES}
              defaultQuestion={null}
            />
          </div>
        )}
      </div>
    </div>
  );
}

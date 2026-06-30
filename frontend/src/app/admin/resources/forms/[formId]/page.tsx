"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ArrowLeft, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api";
import "akvo-react-form-editor/dist/index.css";

// Silence the React 19 element.ref deprecation warning
if (typeof window !== "undefined") {
  const originalError = console.error;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  console.error = function (...args: any[]) {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Accessing element.ref was removed in React 19")
    ) {
      return;
    }
    originalError.apply(console, args);
  };

  const originalWarn = console.warn;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  console.warn = function (...args: any[]) {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Accessing element.ref was removed in React 19")
    ) {
      return;
    }
    originalWarn.apply(console, args);
  };
}

// Polyfill React secret internals for legacy package compatibility under React 19
if (React) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const r = React as any;
  if (!r.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED) {
    r.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = {
      ReactCurrentDispatcher: {
        current: null,
      },
      ReactCurrentBatchConfig: {
        transition: null,
      },
    };
  }

  // React 19 ref property compatibility polyfill
  const originalCreateElement = r.createElement;
  if (originalCreateElement && !originalCreateElement.__refPolyfilled) {
    const newCreateElement = function (
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      type: any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      props: any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ...children: any[]
    ) {
      const element = originalCreateElement.apply(React, [
        type,
        props,
        ...children,
      ]);
      if (
        element &&
        typeof element === "object" &&
        typeof type !== "string" &&
        props &&
        props.ref !== undefined
      ) {
        try {
          const clonedElement = Object.create(Object.getPrototypeOf(element));

          // Copy all string properties
          Object.getOwnPropertyNames(element).forEach((key) => {
            if (key === "ref") {
              Object.defineProperty(clonedElement, "ref", {
                get() {
                  return this.props?.ref;
                },
                configurable: true,
                enumerable: true,
              });
            } else {
              Object.defineProperty(
                clonedElement,
                key,
                Object.getOwnPropertyDescriptor(
                  element,
                  key
                ) as PropertyDescriptor
              );
            }
          });

          // Copy all symbol properties (e.g. $$typeof)
          Object.getOwnPropertySymbols(element).forEach((sym) => {
            Object.defineProperty(
              clonedElement,
              sym,
              Object.getOwnPropertyDescriptor(
                element,
                sym
              ) as PropertyDescriptor
            );
          });

          return clonedElement;
        } catch {
          // Fallback to original element if cloning fails
          return element;
        }
      }
      return element;
    };
    newCreateElement.__refPolyfilled = true;
    r.createElement = newCreateElement;
  }
}

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
        {formData && (
          <div className="arfe-editor-wrapper">
            <WebformEditor
              initialValue={formData}
              onSave={handleSave}
              limitQuestionType={ALLOWED_QUESTION_TYPES}
            />
          </div>
        )}
      </div>
    </div>
  );
}

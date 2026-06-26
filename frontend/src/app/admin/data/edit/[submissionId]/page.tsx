"use client";

import React, { useState, useEffect, use } from "react";
import { apiClient, adminApiClient } from "@/lib/api";
import { ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import L from "leaflet";
import dynamic from "next/dynamic";
import "akvo-react-form/dist/index.css";

// Silence the React 19 element.ref deprecation warning and patch Leaflet double-initialization
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

  // Leaflet double-initialization patch
  if (L) {
    const originalMap = L.map;
    L.map = function (el: string | HTMLElement, options?: L.MapOptions) {
      const container =
        typeof el === "string" ? document.getElementById(el) : el;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (container && (container as any)._leaflet_id) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (container as any)._leaflet_id = null;
      }
      return originalMap.call(L, el, options);
    };

    const originalMapClass = L.Map;
    L.Map = function (el: string | HTMLElement, options?: L.MapOptions) {
      const container =
        typeof el === "string" ? document.getElementById(el) : el;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (container && (container as any)._leaflet_id) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (container as any)._leaflet_id = null;
      }
      return new originalMapClass(el, options);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;
    L.Map.prototype = originalMapClass.prototype;
  }
}

// Polyfill React secret internals and React 19 ref access for legacy package (akvo-react-form) compatibility under React 19
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
        // Bypass cloning for Map/Leaflet components to prevent double-initialization errors
        const name = type && (type.name || type.displayName || "");
        const isMapComponent =
          (props &&
            (props.center !== undefined ||
              props.zoom !== undefined ||
              props.url !== undefined ||
              props.attribution !== undefined ||
              props.position !== undefined)) ||
          (typeof name === "string" &&
            (name.toLowerCase().includes("map") ||
              name.toLowerCase().includes("layer") ||
              name.toLowerCase().includes("marker") ||
              name.toLowerCase().includes("popup") ||
              name.toLowerCase().includes("geojson") ||
              name.toLowerCase().includes("leaflet")));
        if (isMapComponent) {
          return element;
        }

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

interface EditFormPageProps {
  params: Promise<{
    submissionId: string;
  }>;
}

export default function EditFormPage({ params }: EditFormPageProps) {
  const { submissionId } = use(params);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [blueprint, setBlueprint] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [initialValues, setInitialValues] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);

    const fetchData = async () => {
      try {
        const subRes = await adminApiClient.get(`/submissions/${submissionId}`);
        if (!active) return;

        const formId = subRes.data.form_id;
        const bpRes = await apiClient.get(`/forms/${formId}/blueprint`);
        if (!active) return;

        setBlueprint(bpRes.data);

        // Build initial values array for akvo-react-form in format: Array<{ question: number, value: any }>
        const initialVals = subRes.data.answers.map((a: any) => {
          let val: any;
          if (a.options && a.options.length > 0) {
            val = a.options;
          } else if (a.value !== null && a.value !== undefined) {
            val = a.value;
          } else {
            val = a.name || "";
          }
          return {
            question: a.question_id,
            value: val,
          };
        });
        setInitialValues(initialVals);
        setError(null);
      } catch (err: unknown) {
        if (active) {
          const apiErr = err as { response?: { data?: { detail?: string } } };
          setError(
            apiErr.response?.data?.detail ||
              "Failed to fetch submission details"
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      active = false;
    };
  }, [submissionId]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleFinish = async (values: any) => {
    setSubmitting(true);
    setError(null);
    try {
      // Map form output values back to DB payload, filtering out non-numeric metadata keys
      const answersPayload = Object.keys(values)
        .map((qIdStr) => {
          const qId = parseInt(qIdStr, 10);
          if (isNaN(qId)) {
            return null;
          }
          const val = values[qIdStr];
          const isArr = Array.isArray(val);

          return {
            question_id: qId,
            value: isArr ? null : val,
            options: isArr ? val : null,
            index: 0,
          };
        })
        .filter((ans) => ans !== null);

      const payload = {
        answers: answersPayload,
      };

      await adminApiClient.put(`/submissions/${submissionId}`, payload);
      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/admin/data";
      }, 1500);
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setError(
        apiErr.response?.data?.detail ||
          "Failed to update submission data. Please check your inputs."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
        <p className="text-slate-500 text-sm">
          Fetching submission details and form definition...
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
              Submission Updated Successfully!
            </h2>
            <p className="text-slate-500 text-sm max-w-sm">
              Your modifications have been saved. Redirecting you back to the
              data overview...
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {blueprint ? (
              <div className="prose prose-slate max-w-none">
                <Webform
                  forms={blueprint}
                  initialValue={initialValues}
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
                    Saving modifications...
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

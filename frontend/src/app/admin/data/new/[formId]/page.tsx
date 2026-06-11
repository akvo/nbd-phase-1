'use client';

import React, { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import L from 'leaflet';

// Silence the React 19 element.ref deprecation warning and patch Leaflet double-initialization
if (typeof window !== 'undefined') {
  const originalError = console.error;
  console.error = function(...args: any[]) {
    if (typeof args[0] === 'string' && args[0].includes('Accessing element.ref was removed in React 19')) {
      return;
    }
    originalError.apply(console, args);
  };

  const originalWarn = console.warn;
  console.warn = function(...args: any[]) {
    if (typeof args[0] === 'string' && args[0].includes('Accessing element.ref was removed in React 19')) {
      return;
    }
    originalWarn.apply(console, args);
  };

  // Leaflet double-initialization patch
  if (L) {
    const originalMap = L.map;
    L.map = function(el: any, options: any) {
      const container = typeof el === 'string' ? document.getElementById(el) : el;
      if (container && container._leaflet_id) {
        container._leaflet_id = null;
      }
      return originalMap.call(L, el, options);
    };

    const originalMapClass = L.Map;
    L.Map = function(el: any, options: any) {
      const container = typeof el === 'string' ? document.getElementById(el) : el;
      if (container && container._leaflet_id) {
        container._leaflet_id = null;
      }
      return new originalMapClass(el, options);
    } as any;
    L.Map.prototype = originalMapClass.prototype;
  }
}

// Polyfill React secret internals and React 19 ref access for legacy package (akvo-react-form) compatibility under React 19
if (React) {
  // Silence the React 19 element.ref deprecation warning to prevent Next.js dev overlay from crashing
  if (typeof window !== 'undefined') {
    const originalError = console.error;
    console.error = function(...args: any[]) {
      if (typeof args[0] === 'string' && args[0].includes('Accessing element.ref was removed in React 19')) {
        return;
      }
      originalError.apply(console, args);
    };

    const originalWarn = console.warn;
    console.warn = function(...args: any[]) {
      if (typeof args[0] === 'string' && args[0].includes('Accessing element.ref was removed in React 19')) {
        return;
      }
      originalWarn.apply(console, args);
    };
  }

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
    const newCreateElement = function(type: any, props: any, ...children: any[]) {
      const element = originalCreateElement.apply(React, arguments as any);
      if (element && typeof element === 'object' && typeof type !== 'string' && props && props.ref !== undefined) {
        // Bypass cloning for Map/Leaflet components to prevent double-initialization errors
        const name = type && (type.name || type.displayName || '');
        const isMapComponent = (props && (
          props.center !== undefined ||
          props.zoom !== undefined ||
          props.url !== undefined ||
          props.attribution !== undefined ||
          props.position !== undefined
        )) || (
          typeof name === 'string' && (
            name.toLowerCase().includes('map') ||
            name.toLowerCase().includes('layer') ||
            name.toLowerCase().includes('marker') ||
            name.toLowerCase().includes('popup') ||
            name.toLowerCase().includes('geojson') ||
            name.toLowerCase().includes('leaflet')
          )
        );
        if (isMapComponent) {
          return element;
        }

        try {
          const clonedElement = Object.create(Object.getPrototypeOf(element));

          // Copy all string properties
          Object.getOwnPropertyNames(element).forEach(key => {
            if (key === 'ref') {
              Object.defineProperty(clonedElement, 'ref', {
                get() {
                  return this.props?.ref;
                },
                configurable: true,
                enumerable: true
              });
            } else {
              Object.defineProperty(clonedElement, key, Object.getOwnPropertyDescriptor(element, key) as PropertyDescriptor);
            }
          });

          // Copy all symbol properties (e.g. $$typeof)
          Object.getOwnPropertySymbols(element).forEach(sym => {
            Object.defineProperty(clonedElement, sym, Object.getOwnPropertyDescriptor(element, sym) as PropertyDescriptor);
          });

          return clonedElement;
        } catch (e) {
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

// Dynamically import Webform from akvo-react-form to prevent SSR issues
import dynamic from 'next/dynamic';
import 'akvo-react-form/dist/index.css';

const Webform = dynamic<any>(() => import('akvo-react-form').then((mod) => mod.Webform), {
  ssr: false,
  loading: () => (
    <div className="flex items-center space-x-2 text-slate-500 py-4">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span>Loading webform...</span>
    </div>
  ),
});

interface NewFormPageProps {
  params: Promise<{
    formId: string;
  }>;
}

export default function NewFormPage({ params }: NewFormPageProps) {
  const router = useRouter();
  const { formId } = use(params);
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
          setError(err.response?.data?.detail || 'Failed to fetch form blueprint');
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

  const handleFinish = async (values: any) => {
    setSubmitting(true);
    setError(null);
    try {
      const formType = blueprint?.type;
      const numericFormId = parseInt(formId, 10) || blueprint?.form_id || 1;

      let endpoint = '/internal/submit';
      if (formId === 'fgd' || formType === 3) {
        endpoint = '/internal/fgd';
      } else if (formId === 'lab-qa' || formType === 4) {
        endpoint = '/internal/lab-qa';
      }

      const payload = {
        ...values,
        form_id: numericFormId,
      };

      await apiClient.post(endpoint, payload);
      setSuccess(true);
      setTimeout(() => {
        window.location.href = '/admin/data';
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit data. Please check your inputs.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
        <p className="text-slate-500 text-sm">Fetching form blueprint definition...</p>
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
            <h2 className="text-lg font-bold text-slate-800">Submission Successful!</h2>
            <p className="text-slate-500 text-sm max-w-sm">
              Your data has been successfully ingested. Redirecting you back to the data overview...
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {blueprint ? (
              <div className="prose prose-slate max-w-none">
                <Webform forms={blueprint} onFinish={handleFinish} />
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-200 rounded-xl">
                <p className="text-slate-400 text-sm">No blueprint definition was loaded.</p>
              </div>
            )}

            {submitting && (
              <div className="fixed inset-0 bg-slate-900/25 backdrop-blur-sm flex items-center justify-center z-50">
                <div className="bg-white rounded-xl p-6 shadow-lg border border-slate-100 flex items-center space-x-4 max-w-xs">
                  <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
                  <span className="text-sm font-medium text-slate-700">Submitting response...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect } from "react";

/**
 * Polyfills React 19 for legacy packages (e.g. akvo-react-form, akvo-react-form-editor)
 * that depend on deprecated React APIs or internals.
 *
 * @param L Optional Leaflet instance to apply double-initialization patching
 */
export function initReactCompat(L?: any) {
  if (typeof window === "undefined") return;

  // 1. Silence the React 19 element.ref deprecation warnings
  const originalError = console.error;
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
  console.warn = function (...args: any[]) {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Accessing element.ref was removed in React 19")
    ) {
      return;
    }
    originalWarn.apply(console, args);
  };

  // 2. Leaflet double-initialization patch (if L is provided)
  if (L) {
    const originalMap = L.map;
    L.map = function (el: string | HTMLElement, options?: any) {
      const container =
        typeof el === "string" ? document.getElementById(el) : el;
      if (container && (container as any)._leaflet_id) {
        (container as any)._leaflet_id = null;
      }
      return originalMap.call(L, el, options);
    };

    const originalMapClass = L.Map;
    L.Map = function (el: string | HTMLElement, options?: any) {
      const container =
        typeof el === "string" ? document.getElementById(el) : el;
      if (container && (container as any)._leaflet_id) {
        (container as any)._leaflet_id = null;
      }
      return new originalMapClass(el, options);
    } as any;
    L.Map.prototype = originalMapClass.prototype;
  }

  // 3. Polyfill React secret internals (__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED)
  // Proxy them to React 19's client internals to resolve active dispatcher issues
  if (React) {
    const r = React as any;
    if (!r.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED) {
      Object.defineProperty(
        r,
        "__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED",
        {
          get() {
            return (
              r.__CLIENT_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED || {
                ReactCurrentDispatcher: {
                  current: null,
                },
                ReactCurrentBatchConfig: {
                  transition: null,
                },
              }
            );
          },
          configurable: true,
          enumerable: true,
        }
      );
    }

    // React 19 ref property compatibility polyfill for custom/legacy components
    const originalCreateElement = r.createElement;
    if (originalCreateElement && !originalCreateElement.__refPolyfilled) {
      const newCreateElement = function (
        type: any,
        props: any,
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
            return element;
          }
        }
        return element;
      };
      newCreateElement.__refPolyfilled = true;
      r.createElement = newCreateElement;
    }
  }
}

/**
 * Custom hook to dynamically load and unload stylesheets.
 * Ensures CSS is added to document head on mount and cleanly removed on unmount.
 *
 * @param href The public path/URL of the stylesheet
 */
export function useDynamicStylesheet(href: string) {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const id = `dynamic-style-${href.replace(/[^a-zA-Z0-9]/g, "-")}`;
    let link = document.getElementById(id) as HTMLLinkElement;

    if (!link) {
      link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }

    return () => {
      const activeLink = document.getElementById(id);
      if (activeLink) {
        activeLink.parentNode?.removeChild(activeLink);
      }
    };
  }, [href]);
}

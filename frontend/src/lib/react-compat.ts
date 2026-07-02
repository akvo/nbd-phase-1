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

  // 1. Silence deprecation and internal design warnings from legacy dependencies (e.g., React 19 element.ref, antd, state-in-render warnings)
  const originalError = console.error;
  console.error = function (...args: any[]) {
    if (
      typeof args[0] === "string" &&
      (args[0].includes("Accessing element.ref was removed in React 19") ||
        args[0].includes("Tabs.TabPane is deprecated") ||
        args[0].includes(
          "Modal] `visible` will be removed in next major version"
        ) ||
        args[0].includes(
          "Form.Item] A `Form.Item` with a `name` prop must have a single child element"
        ) ||
        (args[0].includes("Cannot update a component") &&
          args[0].includes("while rendering a different component")))
    ) {
      return;
    }
    originalError.apply(console, args);
  };

  const originalWarn = console.warn;
  console.warn = function (...args: any[]) {
    if (
      typeof args[0] === "string" &&
      (args[0].includes("Accessing element.ref was removed in React 19") ||
        args[0].includes("Tabs.TabPane is deprecated") ||
        args[0].includes(
          "Modal] `visible` will be removed in next major version"
        ) ||
        args[0].includes(
          "Form.Item] A `Form.Item` with a `name` prop must have a single child element"
        ) ||
        (args[0].includes("Cannot update a component") &&
          args[0].includes("while rendering a different component")))
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

/**
 * Hook that captures a snapshot of all <style> elements in <head> on mount,
 * then on unmount removes any new <style> tags that were injected during the
 * component's lifetime (e.g. by Ant Design). This prevents third-party styles
 * from persisting in the DOM when navigating away from the page.
 *
 * Additionally injects a runtime "protection" style tag AFTER Ant Design's
 * styles have loaded. Since it appears LAST in the <head>, its !important rules
 * beat Ant Design's unlayered styles (which would otherwise beat Tailwind's
 * @layer utilities).
 */
export function useAntdStyleCleanup() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Snapshot all existing style elements before the component mounts
    const existingStyles = new Set(
      Array.from(document.head.querySelectorAll("style"))
    );

    // Use a MutationObserver to intercept newly injected <style> tags.
    // We wrap their content in @layer antd { } to demote their priority below
    // all Tailwind layers (@layer antd declared before @import tailwindcss in globals.css).
    const injectedStyles: HTMLStyleElement[] = [];
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node instanceof HTMLStyleElement && !existingStyles.has(node)) {
            injectedStyles.push(node);
            // Wrap content in @layer antd to lower its cascade priority
            const content = node.textContent || "";
            // Avoid double-wrapping or wrapping empty/already-layered content
            if (content.trim() && !content.includes("@layer")) {
              node.textContent = `@layer antd { ${content} }`;
            }
          }
        }
      }
    });

    observer.observe(document.head, { childList: true });

    return () => {
      observer.disconnect();
      // Remove all style tags that were injected while we were mounted
      for (const style of injectedStyles) {
        if (style.parentNode) {
          style.parentNode.removeChild(style);
        }
      }
    };
  }, []);
}

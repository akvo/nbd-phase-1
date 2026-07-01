"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DropdownMenuProps {
  children: React.ReactNode;
}

interface SharedProps {
  open?: boolean;
  setOpen?: (open: boolean) => void;
}

export function DropdownMenu({ children }: DropdownMenuProps) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { open, setOpen } as SharedProps);
        }
        return child;
      })}
    </div>
  );
}

interface DropdownMenuTriggerProps extends SharedProps {
  children: React.ReactNode;
  asChild?: boolean;
}

export function DropdownMenuTrigger({
  children,
  asChild,
  open,
  setOpen,
}: DropdownMenuTriggerProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    setOpen?.(!open);
  };

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<{
      onClick?: (e: React.MouseEvent) => void;
    }>;
    return React.cloneElement(child, {
      onClick: (e: React.MouseEvent) => {
        if (typeof child.props.onClick === "function") {
          child.props.onClick(e);
        }
        handleClick(e);
      },
    });
  }

  return (
    <button type="button" onClick={handleClick}>
      {children}
    </button>
  );
}

interface DropdownMenuContentProps extends SharedProps {
  children: React.ReactNode;
  align?: "left" | "right";
  side?: "top" | "bottom";
}

export function DropdownMenuContent({
  children,
  align = "right",
  side = "bottom",
  open,
  setOpen,
}: DropdownMenuContentProps) {
  if (!open) return null;

  return (
    <div
      className={cn(
        "absolute right-0 z-50 rounded-lg border border-slate-200 bg-white p-1 shadow-md ring-1 ring-black/5 focus:outline-none",
        side === "top" ? "bottom-full mb-1" : "top-full mt-1",
        align === "left" && "left-0 right-auto"
      )}
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { setOpen } as SharedProps);
        }
        return child;
      })}
    </div>
  );
}

interface DropdownMenuItemProps extends SharedProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

export function DropdownMenuItem({
  children,
  onClick,
  setOpen,
  className,
  disabled = false,
}: DropdownMenuItemProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (disabled) return;
    onClick?.();
    setOpen?.(false);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-center px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 hover:text-slate-900 rounded-md font-medium transition-colors cursor-pointer text-left disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
    >
      {children}
    </button>
  );
}

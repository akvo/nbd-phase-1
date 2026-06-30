import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function isVideoUrl(url?: string | null): boolean {
  if (!url) return false;
  const cleanUrl = url.split("?")[0].toLowerCase();
  return (
    cleanUrl.endsWith(".mp4") ||
    cleanUrl.endsWith(".mov") ||
    cleanUrl.endsWith(".avi") ||
    cleanUrl.endsWith(".webm") ||
    cleanUrl.endsWith(".3gp") ||
    cleanUrl.endsWith(".mkv")
  );
}

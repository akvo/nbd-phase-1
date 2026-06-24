"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SitesIndexPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/admin/resources/users");
  }, [router]);

  return null;
}

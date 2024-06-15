"use client";
import React, { useEffect } from "react";
import { getCookie } from "@/lib/cookie";
import { useRouter } from "next/navigation";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const token = getCookie("token");
  const router = useRouter();

  useEffect(() => {
    if (token) {
      if (typeof window !== "undefined") {
        router.push("/");
      }
    }
  }, [token, router]);

  return <>{children}</>;
};

export default Layout;

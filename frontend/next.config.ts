import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.0.35"],
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/admin/login",
        destination: `${backend}/admin/login`,
      },
      {
        source: "/admin/logout",
        destination: `${backend}/admin/logout`,
      },
      {
        source: "/admin/monthly/excel",
        destination: `${backend}/admin/monthly/excel`,
      },
      {
        source: "/admin/payslip/pdf/:worker/:year/:month",
        destination: `${backend}/admin/payslip/pdf/:worker/:year/:month`,
      },
    ];
  },
};

export default nextConfig;

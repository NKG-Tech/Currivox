/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://currivox-1.onrender.com/:path*",
      },
    ];
  },
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow ngrok tunnel domains to connect to the dev server (HMR)
  allowedDevOrigins: ["*.ngrok-free.app", "*.ngrok-free.dev", "*.ngrok.io"],

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8001/api/:path*",
      },
    ];
  },
};

export default nextConfig;

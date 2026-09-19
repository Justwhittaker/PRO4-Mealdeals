/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.dineadeal.com" }],
        destination: "https://dineadeal.com/:path*",
        permanent: true,
      },
      {
        source: "/gb",
        destination: "/uk",
        permanent: true,
      },
      {
        source: "/gb/:path*",
        destination: "/uk/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;

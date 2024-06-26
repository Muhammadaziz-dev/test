/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: false,
    env: {
        API: "http://127.0.0.1:8000/api"
    },
    images: {
        remotePatterns: [{protocol: "https", hostname: "*"}, {protocol: "http", hostname: "*"},],
    },
};

export default nextConfig;

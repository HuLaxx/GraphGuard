/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,

    // Enable typed routes (stable in Next.js 16)
    typedRoutes: true,

    // API rewrites for backend proxy
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8000/:path*',
            },
            {
                source: '/graphql',
                destination: 'http://localhost:8000/graphql',
            },
        ];
    },

    // Image optimization
    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: 'localhost',
            },
        ],
    },
};

module.exports = nextConfig;

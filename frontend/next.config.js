/** @type {import('next').NextConfig} */
const apiPort = process.env.NEXT_PUBLIC_API_PORT || process.env.API_PORT || '8000';
const apiBase =
    (process.env.NEXT_PUBLIC_API_BASE || process.env.API_BASE || `http://localhost:${apiPort}`).replace(
        /\/$/,
        ''
    );

const nextConfig = {
    reactStrictMode: true,

    // Enable typed routes (stable in Next.js 16)
    typedRoutes: true,

    // API rewrites for backend proxy
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${apiBase}/:path*`,
            },
            {
                source: '/graphql',
                destination: `${apiBase}/graphql`,
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

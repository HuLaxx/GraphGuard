/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,

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

    // Enable experimental features
    experimental: {
        typedRoutes: true,
    },

    // Image optimization
    images: {
        domains: ['localhost'],
    },
};

module.exports = nextConfig;

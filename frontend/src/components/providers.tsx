"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ApolloProvider } from "@apollo/client";
import { useEffect, useState } from "react";
import { apolloClient } from "@/lib/apollo-client";
import { ErrorBoundary } from "@/components/ui/error-boundary";

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 60 * 1000, // 1 minute
                        refetchOnWindowFocus: false,
                    },
                },
            })
    );
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    return (
        <QueryClientProvider client={queryClient}>
            <ApolloProvider client={apolloClient}>
                <ErrorBoundary>
                    {children}
                </ErrorBoundary>
            </ApolloProvider>
            {process.env.NODE_ENV === "development" && isMounted && (
                <ReactQueryDevtools initialIsOpen={false} />
            )}
        </QueryClientProvider>
    );
}

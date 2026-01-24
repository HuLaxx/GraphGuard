import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";

const apiKey = process.env.NEXT_PUBLIC_API_KEY;

const httpLink = createHttpLink({
    uri: process.env.NEXT_PUBLIC_GRAPHQL_URL || "/graphql",
    headers: apiKey ? { "X-API-Key": apiKey } : undefined,
});

export const apolloClient = new ApolloClient({
    link: httpLink,
    cache: new InMemoryCache({
        typePolicies: {
            Query: {
                fields: {
                    fraudQueue: {
                        keyArgs: ["status"],
                        merge(existing, incoming) {
                            return incoming;
                        },
                    },
                },
            },
        },
    }),
    defaultOptions: {
        watchQuery: {
            fetchPolicy: "cache-and-network",
        },
    },
});

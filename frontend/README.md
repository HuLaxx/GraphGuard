# GraphGuard - Frontend

Next.js dashboard for fraud investigators with Radix UI + Tailwind and D3.js network visualization.

## Tech Stack (from Specification.md Lines 56-64)
- React 18.2
- TypeScript 5.3
- Apollo Client 3.8 (GraphQL)
- Radix UI + Tailwind CSS
- D3.js 7.8 (Network graphs)
- Recharts 2.10 (SHAP charts)
- React Query 5.0

## Getting Started

```bash
npm install
npm run dev
```

## Key Components
- `FraudQueue` - Case queue with pagination
- `CaseDetail` - Investigation workspace
- `NetworkGraph` - D3.js force-directed graph
- `ShapChart` - SHAP feature importance
- `RagAssistant` - Investigator copilot (RAG)

## Environment

```
NEXT_PUBLIC_RAG_API_URL=http://localhost:8000
NEXT_PUBLIC_RAG_ALLOW_INGEST=true
```

## Reference
See [Specification.md Lines 3146-3770](../Specification.md) for detailed implementation.

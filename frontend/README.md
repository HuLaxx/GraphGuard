# GraphGuard - Frontend

React SPA for fraud investigators with Material-UI and D3.js network visualization.

## Tech Stack (from Specification.md Lines 56-64)
- React 18.2
- TypeScript 5.3
- Apollo Client 3.8 (GraphQL)
- Material-UI 5.14
- D3.js 7.8 (Network graphs)
- Recharts 2.10 (SHAP charts)
- React Query 5.0

## Getting Started

```bash
pnpm install
pnpm dev
```

## Key Components
- `FraudQueue` - Case queue with pagination
- `CaseDetail` - Investigation workspace
- `NetworkGraph` - D3.js force-directed graph
- `ShapChart` - SHAP feature importance

## Reference
See [Specification.md Lines 3146-3770](../Specification.md) for detailed implementation.

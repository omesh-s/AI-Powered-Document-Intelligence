# docintel-web

React + Vite + TypeScript console for **Document Intelligence**.

## Configuration

- **Local**: `vite.config.ts` proxies `/api` to `http://127.0.0.1:8000`. Ensure `API_CORS_ORIGINS` on the API includes `http://localhost:5173`.
- **Production build**: static assets expect `/api` to be routed to your API origin (reverse proxy) unless you introduce a `VITE_*` base URL pattern.

## Scripts

```bash
npm install
npm run dev      # http://localhost:5173 — proxies /api → http://127.0.0.1:8000
npm run build
npm test         # Vitest + Testing Library
npm run lint
```

## Requirements

- API running with CORS allowing the dev origin (`API_CORS_ORIGINS` includes `http://localhost:5173`).
- Object storage (e.g. MinIO) reachable from the **browser** for presigned **PUT** uploads (`S3_ENDPOINT_URL` must be a URL the browser can reach — use `http://127.0.0.1:9000` or your LAN host, not a Docker-only hostname).

## UX notes

- Citations link to document detail anchors (`#chunk-{uuid}` / `#page-{n}`).
- Query view supports `?document={uuid}` and `?session={uuid}` for scoped and resumed threads.
- Upload errors map API / storage bodies via `formatApiError` in `src/lib/apiClient.ts`.
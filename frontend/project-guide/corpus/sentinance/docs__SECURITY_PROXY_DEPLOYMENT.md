# Trusted ingress, Host and WebSocket Origin deployment gate

**Status: Code and offline tests exist on draft PR #30. No production ingress
or real external DNS/TLS path has been verified. This is not a release approval.**

## Required production configuration

Set each of these using the *actual* deployment topology before starting an
API container with `SENTINANCE_ENV=production`:

| Variable | Requirement |
| --- | --- |
| `SENTINANCE_ENV` | `production` or `staging` (both fail closed) |
| `FRONTEND_URL` | Exact **HTTPS** browser origin, no path, e.g. an actual frontend FQDN |
| `CORS_ORIGINS` | Optional additional exact HTTPS origins, comma-separated, no `*` |
| `SENTINANCE_ALLOWED_HOSTS` | Required comma-separated exact API Host names, no protocol/port/wildcards |
| `SENTINANCE_TRUSTED_PROXY_IPS` | Literal IP addresses of **verified** reverse-proxy peers; optional default `127.0.0.1` only |
| `PORT` / `API_PORT` | Valid listening port, default 8000 |

Do not copy a fictitious domain or proxy address into deployment settings.
The Docker image now launches `python server.py`, whose default environment
is **production** unless a developer explicitly opts into development mode.
`docker-compose.yml` also sets production mode and binds the API host port to
**127.0.0.1**, not all external interfaces. The frontend Docker port and
separate public ingress must still be audited before deployment.

`infra/k8s/config.yaml` intentionally selects `SENTINANCE_ENV=production`
without inventing a frontend or API FQDN. Both Kubernetes and Compose
production startup **must fail** until `FRONTEND_URL` and
`SENTINANCE_ALLOWED_HOSTS` have been populated with the real public values.

The startup program `apps/api/server.py` passes the parsed trusted literal
peer IPs to Uvicorn's `forwarded_allow_ips`. Wildcards, `0.0.0.0/0`,
hostname entries, unspecified addresses and malformed lists are rejected.
A source IP that is not trusted must not rewrite its address or scheme via
`X-Forwarded-For` or `X-Forwarded-Proto`.

## Browser/WebSocket protection

HTTP CORS alone does **not** enforce a browser WebSocket's Origin. The
`/ws/prices` endpoint therefore closes unapproved or missing `Origin`
during handshake with code 1008 *before* accepting or allocating a manager
connection. Valid origins must match the exact configured browser allowlist.
The origin check is **not** authentication: a non-browser client can forge
`Origin`. Additional authentication, per-user authorization and connection
rate limits are separate gates before exposing private data.

Only use WSS through a TLS-terminating ingress. The ingress must forward
WebSocket Upgrade headers correctly, restrict direct access to internal API
ports, prevent arbitrary client-supplied forwarded headers from being trusted,
and terminate TLS at a managed trust boundary.

## Release verification (all open until real ingress tested)

- [ ] Establish the actual API and frontend DNS FQDNs; obtain TLS certificates.
- [ ] Determine exact **network-peer** ingress IPs; no wildcard proxy trust.
- [ ] Confirm startup fails without required production domains or with
  malformed/wildcard origin/Host values.
- [ ] Confirm a valid HTTPS origin and Host work behind the real ingress.
- [ ] Confirm unknown/missing/null WebSocket Origin is rejected before accept.
- [ ] Confirm forged `Host` and untrusted `X-Forwarded-For` / `X-Forwarded-Proto`
  cannot change the server's routing or accepted peer identity.
- [ ] Test WSS Upgrade and idle timeout across a deployed ingress and
  independently running API replicas.
- [ ] Define per-IP and per-user connection/rate limits, authentication for
  protected channels, and safe logging of rejected handshakes.
- [ ] Inspect final exact-head CI, security scan and operator sign-off.
- [ ] Retain human approval before merge, cloud spend or production rollout.

The connected Redis Pub/Sub delivery proof in PR #29 covers two isolated
processes on a GitHub runner; it is not a deployed ingress test or guarantee
of durable replay.

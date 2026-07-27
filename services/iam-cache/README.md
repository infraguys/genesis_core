# Exordos IAM Cache

`exordos-iam-cache` is an in-memory caching proxy for the Exordos Core IAM
introspection and JWKS endpoints.

The public listener preserves the existing Core routes:

- `GET /v1/iam/clients/{client_uuid}/actions/introspect`
- `GET /v1/iam/clients/{client_uuid}/actions/jwks`

All other IAM client requests are forwarded unchanged to Core and are never
cached. Any request carrying `X-OTP`, including a token request, also bypasses
the cache. Successful introspection responses without `X-OTP` are cached by
access token. The token UUID is read from the validated access token's `jti`
claim and is used by the reverse index.

The internal listener exposes an idempotent invalidation endpoint:

```text
DELETE /internal/v1/cache/introspection/{token_uuid}
```

Core does not call this endpoint in the first implementation. Until that
integration is added, introspection entries expire only by their configured
TTL, the access token expiration, or capacity eviction.

JWKS responses use a separate cache keyed by IAM client UUID and a separate
TTL.

## Configuration

The deployment example is
[`../../etc/exordos_core/iam_cache.json.example`](../../etc/exordos_core/iam_cache.json.example).
Cache lifetimes and the upstream request timeout use Go duration syntax such
as `15s`, `5m`, or `1h`. The deployed defaults are 15 seconds for
introspection and one minute for JWKS.

The internal listener defaults to loopback. If it is exposed outside the host,
protect it with the deployment's service-to-service authentication layer.

## Run

```bash
go run ./cmd/exordos-iam-cache \
  -config ../../etc/exordos_core/iam_cache.json.example
```

## Test

```bash
go test -race ./...
go vet ./...
```

---
title: genesis push
---

## Overview

`genesis push` **publishes** your built elements to a Exordos repository, making them available for deployment and for other platform users to consume.

The command reads the **`genesis/genesis.yaml`** file to identify where to push the elements. The `push` section defines one or more target repositories — local filesystem directories or remote HTTP endpoints.

```bash
genesis push [OPTIONS] [PROJECT_DIR]
```

Key options:

| Option | Description |
|---|---|
| `-c, --genesis-cfg-file TEXT` | Name of the project configuration file (default: `genesis.yaml`) |
| `-t, --target TEXT` | Target repository to push to (if multiple are defined) |
| `-e, --element-dir PATH` | Directory where element artifacts are stored (default: `output/`) |
| `-f, --force` | Force push even if the element already exists |
| `-l, --latest` | Also push the element as the `latest` version (for stable versions) |

You can push elements to the [public Exordos Core repository](public-installation.md). Or you can deploy a [private Exordos Core installation](private-installation.md) on your own hardware. For development and testing, you can use [local laptop installation](local-laptop-installation.md).

---

## Getting Started

### Basic Push

From your project directory after a successful build:

```bash
genesis push
```

The command reads `genesis.yaml`, finds the push configuration, and uploads the element artifacts from the `output/` directory to the configured repositories.

### Push to Specific Target

If your `genesis.yaml` defines multiple repositories, specify which one to push to:

```bash
genesis push --target local
```

### Force Push

Overwrite an existing element version:

```bash
genesis push --force
```

### Push as Latest

For stable releases, also tag the element as `latest`:

```bash
genesis push --latest
```

---

## Push Configuration

### Configuration in genesis.yaml

The `push` section in `genesis.yaml` defines where elements are published. You can configure multiple repositories:

```yaml
push:
  local:
    driver: fs
    path: /var/lib/exordos-pools/http
  remote:
    driver: nginx
    url: https://repository.genesis-core.tech
```

| Repository Type | Description |
|---|---|
| `local` | Local filesystem directory. Elements are copied directly to the specified path. |
| `remote` | Remote HTTP repository. Elements are pushed via HTTP to the configured URL. |

### Driver Types

| Driver | Description |
|---|---|
| `fs` | Filesystem driver. Copies artifacts to a local directory path. |
| `nginx` | HTTP driver. Uploads artifacts to an HTTP/HTTPS endpoint, typically an Nginx-served repository. |

### Separate Configuration File

Push configuration can also be stored in a separate file, for example `genesis.push.yaml`:

```yaml
push:
  staging:
    driver: fs
    path: /var/lib/exordos-pools/staging
  production:
    driver: nginx
    url: https://repo.genesis-core.tech/production
```

To use a separate configuration file, specify it with the `-c` option:

```bash
genesis push -c genesis.push.yaml
```

---

## Next Steps

After a successful push, your element is available in the registry and ready for:

- [`genesis deploy`](deploy.md) — deploy the element to a Exordos installation
- Sharing with other developers in your organization

---

## Troubleshooting

If you encounter issues while pushing elements — such as repository connection failures, authentication errors, or upload problems — refer to the [Troubleshooting Guide](troubleshooting.md) for detailed solutions and common fixes.

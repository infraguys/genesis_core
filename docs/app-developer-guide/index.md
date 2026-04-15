---
title: Application Developer Guide
---

This guide walks you through everything you need to build, publish, and deploy **elements** — the name Genesis Core gives to applications — on the platform.

## Quick Start

### 1. Initialize your element

Set up an existing project as a Genesis Core element. The `genesis init` command launches an interactive wizard that generates all required configuration files — including manifests, and a `genesis.yaml` file that describes the build, publish, and deploy procedures.

```bash
genesis init
```

After the wizard completes, your project will contain necessary configuration files — including manifests — that describe your element to the platform.

[Learn more →](init.md)

---

### 2. Build your element

Compile and package your element along with all its artifacts. Genesis Core uses the build configuration defined in `genesis.yaml` to produce a distributable artifact.

```bash
genesis build
```

On success, the build output (container image, binary, or other artifact type) is stored locally and tagged with the current element version.

[Learn more →](build.md)

---

### 3. Publish your element

Push the built element to the Genesis ecosystem registry so it becomes available to other platform users.

```bash
genesis push
```

The element is versioned and pushed to the configured repository based on the metadata in `genesis.yaml`.

[Learn more →](push.md)

---

### 4. Deploy your element

Install and run your element on a Genesis Core platform installation.

```bash
genesis elements install <element-name>
```

The platform resolves dependencies, installs the target element, and starts it in the chosen realm.

[Learn more →](deploy.md)

---

## Walkthrough: Your First Element

Let's walk through platformizing a real FastAPI project from `https://github.com/infraguys/todo_application`.

This is a simple ToDo List API with PostgreSQL persistence. The goal here is not to explore the business logic, but to demonstrate how to take an existing application and platformize it using Genesis Core.

### Prerequisites

To follow this walkthrough, you need a running Genesis installation and the necessary tools.

**Genesis** — you can use either:

- A **public Genesis installation** — hosted at [genesis-core.tech](https://genesis-core.tech). No setup required; just create an account and start using the platform.
- A **private Genesis installation** — your own self-hosted instance. This document describes how to set one up: [Setting up a private installation](../admin-guide/index.md).

Install the necessary tools below.

Install Genesis CLI:

```bash
curl -fsSL https://repository.genesis-core.tech/install.sh | sudo sh
```

The Packer [version 1.9.2](https://hashicorp-releases.yandexcloud.net/packer/1.9.2/) or earlier due to licensing limitation. Download and place into `/usr/local/bin/` or any other directory in your `$PATH`.

The Qemu:

```bash
sudo apt update
sudo apt install qemu-kvm mkisofs
sudo adduser $USER kvm
```

You may need to relogin to apply the changes. Now you are ready to build your element.

### Initialize the project

Clone the project:

```bash
git clone https://github.com/infraguys/todo_application.git && cd todo_application
```

The `genesis init` command allows you to initialize a new element interactively but you can also use it with flags. We will use the flags approach here to speed things up.

```bash
genesis init \
  --project-name todo_application \
  --project-type python \
  --project-systemd-services "todo-api" \
  --project-url "https://github.com/infraguys/todo_application" \
  --project-python-package-manager "pip" \
  --enable-pgsql \
  --author-name "Developer" \
  --author-email "dev@example.com" \
  --manifest-description "A simple ToDo list element" \
  --repository "https://repository.genesis-core.tech/genesis-elements" \
  --pgsql-usage-mode "own_cluster" \
  --pgsql-database-name "todo_api" \
  --pgsql-username "todo_api" \
  --ci-cd "none"
```

After executing this command, a summary will be displayed with the results of the initialization, showing the main configuration files. Study them to understand what was created.

The project is ready to be built and pushed as a Genesis Core element.

### Build the element

To build the element, run:

```bash
genesis build
```

### Push to repository

Use the repository of your genesis installation and push the element:

```bash
genesis push -c genesis.push.yaml
```

### Deploy the element

```bash
genesis elements install todo-api
```

The ToDo API is now available at the configured endpoint.

---

## Advanced Usage

Once you're comfortable with the basics, explore the more in-depth topics below.

- [Writing a manifest from scratch](../misc/manifests.md) — understand the full manifest specification and author one by hand without relying on the `genesis init` wizard.
- [Setting up a private platform installation](../admin-guide/index.md) — spin up your own Genesis Core instance to develop and test your elements end-to-end without connecting to a remote environment.
- [Public Genesis installation](https://genesis-core.tech) — use the hosted Genesis platform without managing your own infrastructure.

![Tests workflow](https://github.com/infraguys/exordos_core/actions/workflows/tests.yml/badge.svg)
![Build workflow](https://github.com/infraguys/exordos_core/actions/workflows/build.yml/badge.svg)

<p align="center">
<img height="256" src="logo.svg" alt="exordos core svg logo">
</p>

Welcome to Exordos Core!

The Exordos Core is an open source software that offers a one turnkey solution to deal with infrastructure at all levels - from bare metal and virtual machines to applications and services.

Refer to the [wiki](https://github.com/infraguys/exordos_core/wiki) for more detailed information.

# 📦 Installation

There are several ways to install Exordos Core and depend on your purpose you can choose one of them.

## Try it out

If you want to try Exordos Core in a few minutes, download the `all-in-one` [stand](https://github.com/infraguys/gci_dev_all_in_one). It's a ready-to-go virtual machine image with preinstalled Exordos Core and ability to get full functionality such as creating inner(nested) virtual machines, installation elements and many others.
This stand may be used for development purposes as well if you are focusing on a new element development.

## Basic usage

In a case you would like to run Exordos Core on your own infrastructure, you can use the [basic guide](https://github.com/infraguys/exordos_core/wiki/BasicUsage) for more details.

# 🚀 Development

**Ubuntu:**

```bash
sudo apt-get install build-essential python3.12-dev python3.12-venv \
    libev-dev libvirt-dev curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME"/.local/bin/env
uv tool install tox --with tox-uv
```

**Fedora:**

```bash
sudo dnf install gcc libev-devel libvirt-devel curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME"/.local/bin/env
uv tool install tox --with tox-uv 
```

Initialize virtual environment:

```bash
tox -e develop
source .tox/develop/bin/activate
```

Follow the development guide [here](https://github.com/infraguys/exordos_core/wiki/DevelopmentGuide) for more details.

# ⚙️ Tests

**NOTE:** Python version 3.12 is supposed to be used, but you can use other versions

```bash
# Unit tests
tox -e py312

# Functional tests
tox -e py312-functional
```

## Functional tests environment

To run functional tests, export the following environment variables:

```bash
export DATABASE_URI="postgresql://exordos_core:exordos_core@127.0.0.1:5432/exordos_core"
export ADMIN_PASSWORD="admin"
export DEFAULT_CLIENT_SECRET="GenesisCoreSecret"
export GLOBAL_SALT="FOy/2kwwdn0ig1QOq7cestqe"
export HS256_KEY="secret"
```

# 🔗 Related projects

- Exordos SDK is a set of tools for developing Exordos elements. You can find it [here](https://github.com/infraguys/gcl_sdk).
- Exordos DevTools it's a set oftools to manager life cycle of genesis projects. You can find it [here](https://github.com/infraguys/genesis_devtools).

# 💡 Contributing

Contributing to the project is highly appreciated! However, some rules should be followed for successful inclusion of new changes in the project:

- All changes should be done in a separate branch.
- Changes should include not only new functionality or bug fixes, but also tests for the new code.
- After the changes are completed and **tested**, a Pull Request should be created with a clear description of the new functionality. And add one of the project maintainers as a reviewer.
- Changes can be merged only after receiving an approve from one of the project maintainers.

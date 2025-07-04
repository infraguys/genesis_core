![Tests workflow](https://github.com/infraguys/genesis_core/actions/workflows/tests.yml/badge.svg)
![Build workflow](https://github.com/infraguys/genesis_core/actions/workflows/build.yml/badge.svg)

<p align="center">
<img height="256" src="logo.svg" alt="genesis core svg logo">
</p>

Welcome to Genesis Core!

The Genesis Core is an open source software that offers a one turnkey solution to deal with infrastructure at all levels - from bare metal and virtual machines to applications and services.

Refer to the [wiki](https://github.com/infraguys/genesis_core/wiki) for more detailed information.


# 📦 Installation 

There are several ways to install Genesis Core and depend on your purpose you can choose one of them.

## Try it out
**NOTE: Under development**

If you want to try Genesis Core in a few minutes, download the `all-in-one` [stand](https://github.com/infraguys/gci_dev_all_in_one). It's a ready-to-go virtual machine image with preinstalled Genesis Core and ability to get full functionality such as creating inner(nested) virtual machines, installation elements and many others.
This stand may be used for development purposes as well if you are focusing on a new element development.

## Basic usage

In a case you would like to run Genesis Core on your own infrastructure, you can use the [basic guide](https://github.com/infraguys/genesis_core/wiki/BasicUsage) for more details.

# 🚀 Development

**Ubuntu:**
```bash
sudo apt-get install build-essential python3.12-dev python3.12-venv \
    tox libev-dev libvirt-dev
```

**Fedora:**
```bash
sudo dnf install tox gcc libev-devel libvirt-devel
```

Initialize virtual environment:

```bash
tox -e develop
source .tox/develop/bin/activate
```

Follow the development guide [here](https://github.com/infraguys/genesis_core/wiki/DevelopmentGuide) for more details.

# ⚙️ Tests
**NOTE:** Python version 3.12 is supposed to be used, but you can use other versions

```bash
# Unit tests
tox -e py312

# Functional tests
tox -e py312-functional
```

# 🔗 Related projects

- Genesis SDK is a set of tools for developing Genesis elements. You can find it [here](https://github.com/infraguys/gcl_sdk).
- Genesis DevTools it's a set oftools to manager life cycle of genesis projects. You can find it [here](https://github.com/infraguys/genesis_devtools).


# 💡 Contributing

Contributing to the project is highly appreciated! However, some rules should be followed for successful inclusion of new changes in the project:
- All changes should be done in a separate branch.
- Changes should include not only new functionality or bug fixes, but also tests for the new code.
- After the changes are completed and **tested**, a Pull Request should be created with a clear description of the new functionality. And add one of the project maintainers as a reviewer.
- Changes can be merged only after receiving an approve from one of the project maintainers.


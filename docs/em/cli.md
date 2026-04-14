# Examples

## Build element from repository

 Build a Genesis element. The command build all images, manifests and other artifacts required for the element. The manifest in the project may be a raw YAML file or a template using Jinja2 templates. For Jinja2 templates, the following variables are
 available by default:

- {{ version }}: version of the element
- {{ name }}: name of the element
- {{ images }}: list of images
- {{ manifests }}: list of manifests

Go to project directory and run the following command:

```bash
genesis build <element_name>
```

## Install element from repository

```bash
genesis e install <element_name>
```

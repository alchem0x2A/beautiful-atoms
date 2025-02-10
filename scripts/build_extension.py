"""Script to download external wheels needed for building Blender extension for Blender >= 4.2

This script is intended to be run by Blender's Python interpreter.
Additionally, the following tools may also be needed:
- C/C++ compiler
- Python header
"""

import shutil
import tempfile
import toml
import site
import warnings
from pathlib import Path
from pip._internal.operations.freeze import freeze
from pip._internal.commands.wheel import WheelCommand


def get_blender_site_packages():
    site_lists = site.getsitepackages()
    if len(site_lists) > 1:
        warnings.warn("Multiple site packages are present! Only choose first.")
    return [site_lists[0]]


def get_installed_packages():
    """Get a list of packages already installed in Blender's Python environment.
    Exclude any user-installed packages from pip freeze --user
    """
    # freeze() gives a list of version strings like
    # "numpy==1.24.3" etc
    pkg_dict = {}
    # user_sites = [p.split("==")[0]
    #               for p in freeze(user_only=True,
    #                               isolated=True,
    #                               exclude_editable=True)]
    for pkg in freeze(
        isolated=True,
        exclude_editable=True,
        paths=get_blender_site_packages(),
    ):
        pkg_name, version = pkg.split("==")
        if pkg_name not in ("pip", "wheel", "setuptools", "distribute"):
            pkg_dict[pkg_name] = version
    return pkg_dict


def generate_pyproject_toml_for_extension(pyproject_path, existing_packages):
    """Modify the pyproject.toml file section
    `project.optional-dependencies.blender-extension`
    with frozen Blender-installed packages.
    """
    with open(pyproject_path, "r") as f:
        pyproject = toml.load(f)

    if "blender-extension" not in pyproject["project"]["optional-dependencies"]:
        raise ValueError(
            "`blender-extension` dependency not specified. Are you using the latest pyproject.toml?"
        )

    bl_dependencies = [f"{pkg}=={ver}" for pkg, ver in existing_packages.items()]
    pyproject["project"]["optional-dependencies"]["blender-extension"] = bl_dependencies

    return pyproject


def build_wheels(
    root=".",
    source_code="batoms",
    pyproject_path="pyproject.toml",
    wheels_dir="wheels",
    index_url=None,
):
    """Use the frozen Blender 3rd party packages to build the wheels
    (including batoms itself) into `wheels_dir`
    """
    root = Path(root)
    source_code_origin = root / source_code
    pyproject_origin = root / pyproject_path
    existing_packages = get_installed_packages()
    # The wheels dir should be first cleared
    wheels_dir = root / wheels_dir
    # copy the source file to tmpdir for building
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_code_target = tmpdir / source_code
        shutil.copytree(source_code_origin, source_code_target)
        new_pyproject_dict = generate_pyproject_toml_for_extension(
            pyproject_origin, existing_packages
        )
        pyproject_target = tmpdir / pyproject_path
        with open(pyproject_target, "w") as f:
            toml.dump(new_pyproject_dict, f)

        # run the pip wheel builder
        wc = WheelCommand("wheel", "Download wheels for blender extension")
        options = [
            "--wheel-dir",
            wheels_dir.as_posix(),
            "--editable",
            tmpdir.as_posix(),
        ]
        if index_url is not None:
            options += [
                "--index-url",
                str(index_url),
            ]
        # run the command
        wc.main(options)
    return

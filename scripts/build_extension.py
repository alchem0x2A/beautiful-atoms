"""
Script to build and package Blender extensions with external dependencies.
This script is designed to be run inside Blender's Python environment.

Note: Blender 4.2+ is needed!

Additionally, the following tools may be required:
- C/C++ compiler
- Python headers

Usage:
    blender -b -P build_extension.py -- --repo-root . --build-dir build \
        --export-dir export --allow-overwrite
"""

import subprocess
import sys
import shutil
import tempfile
import toml
import site
import warnings
import argparse
from pathlib import Path
from pip._internal.operations.freeze import freeze
from pip._internal.commands.wheel import WheelCommand


def get_platform_string(connector="-"):
    """Determine the current platform string used for Blender extensions."""
    import platform

    system = platform.system()
    machine = platform.machine()

    if system == "Linux" and machine == "x86_64":
        return f"linux{connector}x64"
    elif system == "Darwin":
        return (
            f"macos{connector}x64" if machine == "x86_64" else f"macos{connector}arm64"
        )
    elif system in ["Windows", "Microsoft"]:
        # TODO: may need to confirm windows-arm64
        return f"windows{connector}x64"
    return "unsupported"


def get_blender_bin():
    """Obtain the Blender binary path from the bpy module."""
    try:
        import bpy

        blender_bin = Path(bpy.app.binary_path)
    except ImportError:
        raise ImportError(
            "Cannot import bpy module! Make sure build_extension.py is "
            "executed with Blender's `-P` option."
        )
    return blender_bin


def get_blender_site_packages():
    """Retrieve Blender's default site-packages directory."""
    site_packages = site.getsitepackages()
    if len(site_packages) > 1:
        warnings.warn(
            "Multiple site-packages directories found. " "Using the first one."
        )
    return [site_packages[0]]


def get_installed_packages():
    """Retrieve installed packages within Blender's Python environment."""
    pkg_dict = {}
    for pkg in freeze(
        isolated=True, exclude_editable=True, paths=get_blender_site_packages()
    ):
        pkg_name, version = pkg.split("==")
        if pkg_name not in {"pip", "wheel", "setuptools", "distribute"}:
            pkg_dict[pkg_name] = version
    return pkg_dict


def generate_updated_pyproject(pyproject_path, existing_packages):
    """Modify the `blender-extension` optional dependencies in pyproject.toml."""
    with open(pyproject_path, "r") as f:
        pyproject = toml.load(f)

    if "blender-extension" not in pyproject.get("project", {}).get(
        "optional-dependencies", {}
    ):
        raise ValueError(
            "`blender-extension` dependency not found in pyproject.toml. "
            "Ensure you're using the latest version."
        )

    pyproject["project"]["optional-dependencies"]["blender-extension"] = [
        f"{pkg}=={ver}" for pkg, ver in existing_packages.items()
    ]

    return pyproject


def build_wheels(
    source_code="batoms",
    pyproject="pyproject.toml",
    build_dir="build",
    index_url=None,
    extra_wheels_dirs=[],
):
    """Build wheels for the extension, including Blender-installed packages.
    The build_wheels command will also pack batoms itself into a wheel!
    """
    build_dir = Path(build_dir)
    source_code_origin = Path(source_code)
    pyproject_origin = Path(pyproject)

    existing_packages = get_installed_packages()

    # Clear previous wheels
    wheels_dir = build_dir / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    for f in wheels_dir.glob("*.whl"):
        f.unlink()

    # Temporary build environment
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_code_target = tmpdir / source_code_origin.name
        shutil.copytree(source_code_origin, source_code_target)

        # Update pyproject.toml
        updated_pyproject = generate_updated_pyproject(
            pyproject_origin, existing_packages
        )
        pyproject_target = tmpdir / pyproject_origin.name
        print(pyproject_target)
        with open(pyproject_target, "w") as f:
            toml.dump(updated_pyproject, f)

        # Run pip wheel builder
        wc = WheelCommand("wheel", "Download wheels for Blender extension")
        options = [
            "--wheel-dir",
            wheels_dir.as_posix(),
            "-e",
            tmpdir.as_posix() + "[blender-extension]",
        ]
        if index_url:
            options += ["--index-url", str(index_url)]

        print(f"Running: pip wheel {' '.join(options)}")
        wc.main(options)

    print(f"Build completed. Wheels saved in {wheels_dir}")
    merge_wheels(wheels_dir, extra_wheels_dirs)
    return


def compress_wheels(build_dir, export_dir):
    """Compress the built wheels into a zip archive without building the extension.
    Should only be concerned for single-platform build
    """
    build_dir = Path(build_dir)
    export_dir = Path(export_dir)
    wheels_dir = build_dir / "wheels"

    if not wheels_dir.exists():
        raise FileNotFoundError("No wheels found in build directory.")

    zip_path = export_dir / f"batoms-wheels-{get_platform_string(connector='_')}.zip"
    shutil.make_archive(zip_path.with_suffix(""), "zip", wheels_dir)
    print(f"Compressed wheels saved at: {zip_path}")
    return


def update_blender_manifest(build_dir="build", manifest="blender_manifest.toml"):
    """Update the Blender manifest with built wheels."""
    build_dir = Path(build_dir)
    manifest_path = Path(manifest)
    wheels_dir = build_dir / "wheels"

    wheels_list = [
        f.relative_to(build_dir).as_posix() for f in wheels_dir.glob("*.whl")
    ]

    with open(manifest_path, "r") as f:
        manifest_data = toml.load(f)

    manifest_data["wheels"] = wheels_list
    toml_header = (
        "# blender_manifest.toml generated by build_extension.py, "
        "please do not modify the wheels field.\n"
    )
    manifest_str = toml_header + toml.dumps(manifest_data)

    with open(build_dir / "blender_manifest.toml", "w") as f:
        f.write(manifest_str)

    print(f"Updated manifest at {build_dir / 'blender_manifest.toml'}")
    return


def copy_source_code(source_code="batoms", build_dir="build"):
    """Copy the source code to build_dir"""
    source_code = Path(source_code)
    build_dir = Path(build_dir)
    if not source_code.exists():
        raise FileNotFoundError(f"Source directory {source_code} does not exist.")
    shutil.copytree(source_code, build_dir, dirs_exist_ok=True)
    return


def merge_wheels(wheels_dir, extra_wheels_dirs):
    """Merge additional wheels from other platforms into the primary wheels directory."""
    wheels_dir = Path(wheels_dir)
    extra_wheels_dirs = [Path(d) for d in extra_wheels_dirs]
    if len(extra_wheels_dirs) == 0:
        print("No extra wheels provided, skip.")

    # Check if all extra wheels directories exist
    for extra_dir in extra_wheels_dirs:
        if not extra_dir.exists():
            raise FileNotFoundError(
                f"Warning: Extra wheels directory {extra_dir} does not exist."
            )

    # Ensure all directories contain the same number of wheels
    num_current_wheels = len(list(wheels_dir.glob("*.whl")))
    for extra_dir in extra_wheels_dirs:
        wheel_count = len(list(extra_dir.glob("*.whl")))
        if num_current_wheels != wheel_count:
            raise ValueError(
                f"The number of wheels in {extra_dir} "
                f"({wheel_count} wheels) is different "
                f"from {num_current_wheels} in current platform."
            )

    # Merge wheels while avoiding duplicates
    for extra_dir in extra_wheels_dirs:
        for wheel in extra_dir.glob("*.whl"):
            target_path = wheels_dir / wheel.name
            if not target_path.exists():
                shutil.copy2(wheel, wheels_dir)
                print(f"Merged {wheel.name} from {extra_dir} --> {wheels_dir}")
    return


def clear_dirs(*dirs):
    """Delete specified directories and recreate them."""
    for directory in dirs:
        directory = Path(directory)
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    return


def build_extension(
    blender_bin, build_dir="build", export_dir="export", current_platform_only=False
):
    """Compile the Blender extension from build_dir and export to export_dir."""
    blender_bin = Path(blender_bin)
    build_dir = Path(build_dir)
    export_dir = Path(export_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        blender_bin.as_posix(),
        "--command",
        "extension",
        "build",
        "--source-dir",
        build_dir.as_posix(),
        "--output-dir",
        export_dir.as_posix(),
        "--split-platform",
    ]
    subprocess.run(commands, check=True)
    print(f"Extension build completed. Files exported to {export_dir}")
    if current_platform_only is True:
        platform_string = get_platform_string(connector="_")
        print(f"Current platform is {platform_string}")
        for zip_file in export_dir.glob("batoms-*.zip"):
            if platform_string not in zip_file.name:
                zip_file.unlink()
                print(f"Remove {zip_file.as_posix()} as no extra wheels provided")
    return


def main():
    """Main function to parse arguments and execute build steps."""
    parser = argparse.ArgumentParser(
        description=(
            "Build extension zip files for Beautiful Atoms. "
            "Please provide all options after --"
        )
    )
    parser.add_argument(
        "--repo-root", default=".", help="Root directory of the repository."
    )
    parser.add_argument(
        "--pyproject", default="pyproject.toml", help="Path to pyproject.toml file."
    )
    parser.add_argument(
        "--manifest",
        default="blender_manifest.toml",
        help="Path to blender_manifest.toml.",
    )
    parser.add_argument(
        "--build-dir", default=None, help="Directory to store built files."
    )
    parser.add_argument(
        "--export-dir",
        default=None,
        help="Directory for exported Blender extension files.",
    )
    parser.add_argument(
        "--index-url",
        "-i",
        default=None,
        help="Index URL for pip. Same as the -i option in pip.",
    )
    parser.add_argument(
        "--extra-wheels",
        nargs="*",
        help="Directories containing extra wheels from other platforms.",
    )
    parser.add_argument(
        "--only-compress-wheels",
        "-z",
        action="store_true",
        help="Only compress the wheels without building the extension.",
    )

    # Extract only arguments after `--`
    script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(script_args)

    repo_root = Path(args.repo_root).resolve()
    build_dir = Path(args.build_dir) if args.build_dir else repo_root / "build"
    export_dir = Path(args.export_dir) if args.export_dir else repo_root / "export"
    source_code = repo_root / "batoms"
    pyproject = repo_root / args.pyproject
    manifest = repo_root / args.manifest
    extra_wheels = (
        [Path(ew) for ew in args.extra_wheels] if args.extra_wheels is not None else []
    )
    current_platform_only = len(extra_wheels) == 0

    try:
        # import pdb; pdb.set_trace()
        clear_dirs(build_dir, export_dir)
        copy_source_code(source_code, build_dir)
        build_wheels(
            source_code,
            pyproject,
            build_dir,
            index_url=args.index_url,
            extra_wheels_dirs=extra_wheels,
        )
        if args.only_compress_wheels:
            if len(extra_wheels) > 0:
                raise ValueError(
                    "only_compress_wheels should only be performed when no extra wheels are provided."
                )
            compress_wheels(build_dir, export_dir)
            return
        update_blender_manifest(build_dir, manifest)
        build_extension(get_blender_bin(), build_dir, export_dir, current_platform_only)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

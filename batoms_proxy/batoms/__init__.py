"""Proxy code for dynamically import batoms extension using
`batoms` importable module name.

This proxy only redirectly itself to the active batoms extension if one is found, and does not change the sys.path
"""
import importlib
import sys

try:
    import addon_utils
except ModuleNotFoundError:
    raise ImportError(
        "`addon_utils` cannot be imported. "
        "Make sure you're using Blender's Python interpreter."
    )


class _BatomsProxy:
    """A proxy for dynamically loading the correct Blender extension module.

    The real `batoms` module may exist under different names, like:
    - `bl_ext.user_default.batoms`
    - `bl_ext.some_other_channel.batoms`

    This proxy ensures that `import batoms` works seamlessly,
    regardless of how Blender registers the extension.
    """

    extension_name = "batoms"

    def __init__(self):
        self._module = None
        self._resolved_name = None  # Stores the actual loaded module name

    def _find_extension_module(self):
        """Search for the correct `bl_ext.<channel>.batoms` module dynamically.

        Returns:
            str: The full module name (`bl_ext.<channel>.batoms`) if found.

        Raises:
            ImportError: If no valid module is found or if multiple exist.
        """
        possible_modules = []

        # Get the list of available Blender extensions
        addons = addon_utils.modules()
        if not addons:
            raise ImportError(
                "Blender extension system is unavailable. Ensure that Blender is running."
            )

        for addon in addons:
            importable_name = addon.__name__

            # Ensure the module ends with ".batoms"
            if importable_name.endswith(f".{self.extension_name}"):
                # At least loaded_state must be true
                loaded_default, loaded_state = addon_utils.check(importable_name)
                if loaded_state:
                    possible_modules.append(importable_name)

        # Handle errors if no module or multiple modules exist
        if not possible_modules:
            raise ImportError(
                f"No extension ending with `{self.extension_name}` is enabled in Blender.\n"
                "Please enable the extension in Blender's Preferences > Add-ons."
            )
        elif len(possible_modules) > 1:
            raise ImportError(
                f"Multiple `{self.extension_name}` extensions detected: {possible_modules}. "
                "Please ensure only one extension is active in Blender."
            )

        return possible_modules[0]  # The correct module name

    def _load_module(self):
        """Load the real `batoms` module dynamically when accessed."""
        if self._module is not None:
            return  # Prevent infinite recursion

        module_name = self._find_extension_module()
        self._module = importlib.import_module(module_name)
        self._resolved_name = module_name

    def __getattr__(self, name):
        """Dynamically forward attribute access to `bl_ext.<channel>.batoms`."""
        self._load_module()
        return getattr(self._module, name)

    def __dir__(self):
        """Return attributes of the real module."""
        self._load_module()
        return dir(self._module)

    def __call__(self, *args, **kwargs):
        """If `batoms` is callable, forward the call."""
        self._load_module()
        return self._module(*args, **kwargs)

    def __repr__(self):
        """Return a proper representation."""
        if self._resolved_name:
            return f"<Proxy for {self._resolved_name}>"
        else:
            return f"<Proxy for '{self.extension_name}' (not yet loaded)>"


# Replace current module with the proxy to the actual batoms extension, similar to openbabel
sys.modules[__name__] = _BatomsProxy()

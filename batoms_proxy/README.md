# Proxy code for importing `batoms` module

The folder contains proxy code for importing
the beautiful-atoms code via the `batoms` module name.
It exists to cope with the extension system introduced
in Blender 4.2+, where the actual beautiful-atoms extension
may take different names depending on which way it is installed,
for example:

- `bl_ext.user_default.batoms`: if installed via zip file (drag-drop)
- `bl_ext.blender_org.batoms`: installed via official channel
- `bl_ext.beautiful_atoms.batoms`: installed via beautiful-atoms repo

The proxy code allow scripting in a unified way similar to earlier versions of Blender:
```python
from batoms import Batoms
```

For now the proxy may not be needed if blender.org accepts uploading
the whole batoms wheel in the extension. We'll keep this as a back up
solution.

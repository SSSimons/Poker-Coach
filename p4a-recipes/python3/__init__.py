"""Android-safe wrapper around python-for-android's bundled CPython recipe.

CPython 3.12 can incorrectly enable the Unix ``grp`` iterator when it is
cross-compiled with a recent Android NDK.  Android's libc does not expose
setgrent/getgrent/endgrent, so explicitly disable that optional stdlib module.
The application does not use it.
"""

from importlib.util import module_from_spec, spec_from_file_location
from os.path import dirname, join

import pythonforandroid


_recipe_dir = join(dirname(pythonforandroid.__file__), "recipes", "python3")
_recipe_file = join(_recipe_dir, "__init__.py")
_spec = spec_from_file_location("_casino_coach_builtin_python3", _recipe_file)
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

recipe = _module.recipe
recipe.configure_args = list(recipe.configure_args) + ["py_cv_module_grp=n/a"]

# Keep the bundled recipe's own patch files discoverable.  The local wrapper
# contains no copy of those upstream patches.
recipe.get_recipe_dir = lambda: _recipe_dir

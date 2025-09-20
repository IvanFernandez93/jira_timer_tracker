import importlib, sys, os

# Ensure project root is on sys.path so top-level modules (views, controllers, etc.)
# can be imported when this script runs from the repository root.
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

ok = True
modules = ('views.config_dialog', 'main')
for m in modules:
    try:
        importlib.import_module(m)
        print('OK import', m)
    except Exception as e:
        ok = False
        print('FAILED import', m, repr(e))

sys.exit(0 if ok else 1)

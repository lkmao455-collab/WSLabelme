import sys
print("Python version:", sys.version)
print()

# Check PyQt5
try:
    import PyQt5
    print("PyQt5 import: SUCCESS")
    print("PyQt5 version:", PyQt5.__version__ if hasattr(PyQt5, '__version__') else 'unknown')
except ImportError as e:
    print("PyQt5 import: FAILED")
    print("Error:", e)

print()
print("Python path:")
for i, p in enumerate(sys.path):
    print(f"  {i}: {p}")

print()
# Check module spec
import importlib.util
spec = importlib.util.find_spec('PyQt5')
print(f"PyQt5 module spec: {spec}")
if spec:
    print(f"  origin: {spec.origin}")
    print(f"  submodule_search_locations: {spec.submodule_search_locations}")
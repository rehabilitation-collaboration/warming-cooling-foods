import sys
from pathlib import Path

# Make the project root importable so `import src...` works from tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

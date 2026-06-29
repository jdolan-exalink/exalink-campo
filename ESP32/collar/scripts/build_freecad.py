from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "--pass" in sys.argv:
    pass_index = sys.argv.index("--pass")
    sys.argv = [sys.argv[0], *sys.argv[pass_index + 1 :]]

from exa_collar.build import main


raise SystemExit(main())


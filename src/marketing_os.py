"""Compatibility import for the Experiment 8 Marketing OS engine.

The canonical implementation lives beside its classroom deliverables under
``experiments/experiment-8-ai-marketing-os/src``.  This shim lets repository
tests import ``src.marketing_os`` without changing the existing experiment
layout.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_path = Path(__file__).resolve().parents[1] / "experiments" / "experiment-8-ai-marketing-os" / "src" / "marketing_os.py"
_spec = spec_from_file_location("_experiment8_marketing_os", _path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load Experiment 8 engine: {_path}")
_module = module_from_spec(_spec)
sys.modules.setdefault("_experiment8_marketing_os", _module)
_spec.loader.exec_module(_module)
globals().update({name: getattr(_module, name) for name in getattr(_module, "__all__", [])})
__all__ = getattr(_module, "__all__", [])

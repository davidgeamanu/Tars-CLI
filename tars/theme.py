from rich.console import Console
from .config import get

console = Console(legacy_windows=False)

# colour palette — override any value in ~/.tarsrc [theme]
PRIMARY = get("theme", "primary", "deep_sky_blue1")
DIM     = get("theme", "dim",     "dim")
OK      = get("theme", "ok",      "green")
WARN    = get("theme", "warn",    "yellow")
ERR     = get("theme", "err",     "red")

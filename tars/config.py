import os
import configparser

_cfg = configparser.ConfigParser()
_rc = os.path.expanduser("~/.tarsrc")
if os.path.exists(_rc):
    _cfg.read(_rc)


def get(section: str, key: str, fallback: str) -> str:
    return _cfg.get(section, key, fallback=fallback)


def get_int(section: str, key: str, fallback: int) -> int:
    try:
        return int(_cfg.get(section, key, fallback=str(fallback)))
    except (ValueError, configparser.Error):
        return fallback


def get_bool(section: str, key: str, fallback: bool) -> bool:
    val = _cfg.get(section, key, fallback=str(fallback))
    return val.strip().lower() in ("true", "1", "yes")

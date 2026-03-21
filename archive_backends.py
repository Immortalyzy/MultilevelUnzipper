"""Helpers for selecting extraction backends and probing archives."""

import os
import subprocess

from log_msg import log_msg
from output_decode import classify_archive_result

BACKEND_7Z = "7z"
BACKEND_BANDIZIP = "bandizip"

_BACKEND_DEFINITIONS = {
    BACKEND_7Z: {
        "display_name": "7-Zip",
        "path_key": "zip_executable_path_7z",
        "use_bandizip": False,
    },
    BACKEND_BANDIZIP: {
        "display_name": "Bandizip",
        "path_key": "zip_executable_path_bandizip",
        "use_bandizip": True,
    },
}

_PROBE_CACHE = {}


def _get_settings(settings=None):
    if settings is not None:
        return settings

    from setting import Config

    return Config.get_instance().settings


def _backend_from_name(settings, backend_name, preferred_path=None):
    definition = _BACKEND_DEFINITIONS[backend_name]
    exe_path = settings.get(definition["path_key"], "")
    if preferred_path and definition["use_bandizip"] == settings.get("use_bandizip", False):
        if not exe_path:
            exe_path = preferred_path

    if not exe_path or not os.path.exists(exe_path):
        return None

    return {
        "name": backend_name,
        "display_name": definition["display_name"],
        "exe_path": exe_path,
        "use_bandizip": definition["use_bandizip"],
    }


def resolve_available_backends(settings=None, preferred_path=None):
    """Return configured extraction backends in preferred order."""
    settings = _get_settings(settings)
    preferred = BACKEND_BANDIZIP if settings.get("use_bandizip", False) else BACKEND_7Z
    alternate = BACKEND_7Z if preferred == BACKEND_BANDIZIP else BACKEND_BANDIZIP

    backends = []
    for backend_name in (preferred, alternate):
        backend = _backend_from_name(settings, backend_name, preferred_path=preferred_path)
        if backend:
            backends.append(backend)
    return backends


def clear_archive_probe_cache():
    """Clear cached probe results for the current process."""
    _PROBE_CACHE.clear()


def _probe_cache_key(file_path, backends):
    normalized_file = os.path.abspath(file_path)
    backend_signature = tuple(
        (backend["name"], os.path.normcase(backend["exe_path"])) for backend in backends
    )
    return normalized_file, backend_signature


def _build_probe_args(backend, archive_path):
    return [backend["exe_path"], "l", archive_path]


def probe_archive_with_backends(file_path, settings=None, backends=None):
    """Return True when any configured backend can open file_path as an archive."""
    if not os.path.isfile(file_path):
        return False

    if backends is None:
        backends = resolve_available_backends(settings=settings)
    if not backends:
        return False

    cache_key = _probe_cache_key(file_path, backends)
    if cache_key in _PROBE_CACHE:
        return _PROBE_CACHE[cache_key]

    for backend in backends:
        result = subprocess.run(
            _build_probe_args(backend, file_path),
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        classification = classify_archive_result(result)
        if classification in {"success", "wrong_password"}:
            log_msg(
                f"{backend['display_name']} can open ambiguous file {file_path} as an archive",
                log_level=4,
            )
            _PROBE_CACHE[cache_key] = True
            return True

    _PROBE_CACHE[cache_key] = False
    return False

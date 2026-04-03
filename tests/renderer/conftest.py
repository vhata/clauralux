collect_ignore = []

try:
    import pygame  # noqa: F401
except ImportError:
    collect_ignore.append("test_commentary.py")

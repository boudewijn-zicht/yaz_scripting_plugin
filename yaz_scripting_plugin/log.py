"""Logging configuration."""

import logging

__all__ = ["logger", "set_verbose"]

# Name the logger after the package.
logger = logging.getLogger(__package__)

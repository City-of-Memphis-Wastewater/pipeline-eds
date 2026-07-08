# src/pipeline_eds/chatter.py
from __future__ import annotations
import os
import sys
from contextlib import contextmanager

@contextmanager
def silence_stderr():
    """Temporarily redirect stderr to devnull to mute background browser chatter."""
    new_target = open(os.devnull, "w")
    old_target = sys.stderr
    sys.stderr = new_target
    try:
        yield
    finally:
        sys.stderr = old_target
        new_target.close()

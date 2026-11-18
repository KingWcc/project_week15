"""Test package for the week-15 homework."""

import os

# The tests must never call a real model or require credentials.
os.environ["LLM_MODE"] = "mock"

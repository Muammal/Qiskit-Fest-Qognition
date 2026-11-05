"""Test setup only. Loads contracts before mind, whichever test folder is collected first.

contracts.py and mind/quantum_mind.py import each other. If mind loads first, contracts.quantum_decide
silently falls back to its heuristic stub. See the method notes in docs/SOURCES_REPORT.md.
"""
import contracts  # noqa: F401

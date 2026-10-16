"""Source-only demonstration: this module must never be run by the scanner."""
from importlib import import_module as load
import importlib

raise RuntimeError('Execution trap: inspection must not run this file')
load('plugin')
importlib.import_module('.plugin', package='sample')
__import__(selected_at_runtime)

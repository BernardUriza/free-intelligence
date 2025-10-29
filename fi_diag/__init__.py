"""
fi_diag - Free Intelligence Diagnostic Module

Card: FI-CORE-FEAT-005
Auto-diagnosis module for system health monitoring.

Runs daily checks:
- Docker health
- HDF5 integrity
- API latencies
- Disk space

Usage:
    python -m fi_diag.run
"""

__version__ = "0.1.0"

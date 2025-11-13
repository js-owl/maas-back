#!/usr/bin/env python3
"""
Find a free port on the system
"""
import socket

def find_free_port():
    """Find a free port starting from 8000"""
    for port in range(8000, 8100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free ports found in range 8000-8099")

if __name__ == "__main__":
    port = find_free_port()
    print(f"Free port found: {port}")
    print(f"Use: python -m uvicorn backend.main:app --host 0.0.0.0 --port {port}")

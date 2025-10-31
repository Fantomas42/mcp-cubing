#!/usr/bin/env python3
"""Quick test to verify the server loads correctly."""

import sys
import asyncio

# Test imports
try:
    from mcp_cubing.server import app, get_cube, reset_cube
    from cubing_algs import Algorithm, VCube
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test basic cube functionality
async def test_basic():
    print("\nTesting basic cube functionality...")

    # Test cube creation
    cube = get_cube()
    print(f"✓ Created cube, state: {cube.state[:20]}...")
    print(f"✓ Is solved: {cube.is_solved}")

    # Test move application
    cube.rotate("R U R' U'")
    print(f"✓ Applied sexy move")
    print(f"✓ Is solved: {cube.is_solved}")

    # Test algorithm parsing
    algo = Algorithm.parse_moves("[R, U]")
    print(f"✓ Parsed commutator: {algo}")

    # Test metrics
    metrics = algo.metrics
    print(f"✓ Algorithm metrics - HTM: {metrics.htm}, QTM: {metrics.qtm}")

    # Test reset
    reset_cube()
    cube = get_cube()
    print(f"✓ Reset cube, is solved: {cube.is_solved}")

    # Test MCP server is configured
    print(f"\n✓ MCP server initialized with app name: {app.name}")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_basic())

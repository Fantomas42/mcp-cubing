# ruff: noqa: T201
"""Quick test to verify the server loads correctly."""
import sys

# Test imports
try:
    from cubing_algs import Algorithm

    from mcp_cubing.server import get_cube
    from mcp_cubing.server import mcp
    from mcp_cubing.server import reset_cube
    print('✓ All imports successful')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)


# Test basic cube functionality
def test_basic() -> None:
    """Basic test for checking server integrity."""
    print('\nTesting basic cube functionality...')

    # Test cube creation
    cube = get_cube()
    print(f'✓ Created cube, state: {cube.state[:20]}...')
    print(f'✓ Is solved: {cube.is_solved}')

    # Test move application
    cube.rotate("R U R' U'")
    print('✓ Applied sexy move')
    print(f'✓ Is solved: {cube.is_solved}')

    # Test algorithm parsing
    algo = Algorithm.parse_moves('[R, U]')
    print(f'✓ Parsed commutator: {algo}')

    # Test metrics
    metrics = algo.metrics
    print(f'✓ Algorithm metrics - HTM: {metrics.htm}, QTM: {metrics.qtm}')

    # Test reset
    reset_cube()
    cube = get_cube()
    print(f'✓ Reset cube, is solved: {cube.is_solved}')

    # Test MCP server is configured
    print(f'\n✓ MCP server initialized with name: {mcp.name}')

    print('\n✅ All tests passed!')


if __name__ == '__main__':
    test_basic()

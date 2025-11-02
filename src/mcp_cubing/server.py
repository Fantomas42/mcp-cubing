"""
MCP server for Rubik's cube manipulation and visualization.

This server provides tools for working with virtual Rubik's cubes,
including state management, move execution, visualization
and algorithm analysis.
"""
import asyncio
import json
from typing import Any

from cubing_algs import Algorithm
from cubing_algs import VCube
from cubing_algs.scrambler import scramble
from cubing_algs.transform.mirror import mirror_moves
from cubing_algs.transform.size import compress_moves
from mcp.server import Server  # type: ignore[import-not-found]
from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
from mcp.types import TextContent  # type: ignore[import-not-found]
from mcp.types import Tool

# Global cube state
_cube_state: VCube | None = None


def get_cube() -> VCube:
    """
    Get or initialize the global cube state.

    Returns:
        VCube: The global cube instance.

    """
    global _cube_state  # noqa: PLW0603

    if _cube_state is None:
        _cube_state = VCube()
    return _cube_state


def reset_cube() -> VCube:
    """
    Reset the cube to solved state.

    Returns:
        VCube: The newly reset cube instance.

    """
    global _cube_state  # noqa: PLW0603

    _cube_state = VCube()
    return _cube_state


# Initialize MCP server
app = Server('mcp-cubing')


@app.list_tools()
async def list_tools() -> list[Tool]:  # noqa: RUF029
    """
    List available cube manipulation tools.

    Returns:
        list[Tool]: The list of available MCP tools.

    """
    return [
        Tool(
            name='apply_moves',
            description=(
                'Apply a sequence of moves to the cube. '
                'Supports full WCA notation including wide moves (Rw, Lw), '
                'rotations (x, y, z), and slice moves (M, E, S). '
                'Also supports commutators [A, B] and conjugates [A: B].'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'moves': {
                        'type': 'string',
                        'description': (
                            'Move sequence in standard notation '
                            "(e.g., 'R U R\\' U\\'', 'Rw U2 x', '[R, U]')"
                        ),
                    },
                },
                'required': ['moves'],
            },
        ),
        Tool(
            name='get_state',
            description=(
                'Get the current cube state with optional visualization. '
                'Returns the 54-facelet state string and optional '
                'visual representation.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'display': {
                        'type': 'boolean',
                        'description': (
                            'Whether to include visual representation '
                            '(default: true)'
                        ),
                        'default': True,
                    },
                    'palette': {
                        'type': 'string',
                        'description': (
                            'Color palette for display: '
                            "'default', 'pastel', 'dracula', 'colorblind', etc."
                        ),
                        'default': 'default',
                    },
                    'orientation': {
                        'type': 'string',
                        'description': (
                            'Cube orientation '
                            "(e.g., 'UF' for white top, green front)"
                        ),
                        'default': '',
                    },
                },
            },
        ),
        Tool(
            name='reset_cube',
            description=(
                'Reset the cube to solved state '
                '(all faces with uniform colors).'
            ),
            inputSchema={
                'type': 'object',
                'properties': {},
            },
        ),
        Tool(
            name='scramble_cube',
            description=(
                'Apply a random scramble to the cube. '
                'Generates a random state scramble.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'length': {
                        'type': 'integer',
                        'description': 'Number of random moves (default: 20)',
                        'default': 20,
                    },
                },
            },
        ),
        Tool(
            name='is_solved',
            description='Check if the cube is currently in a solved state.',
            inputSchema={
                'type': 'object',
                'properties': {},
            },
        ),
        Tool(
            name='parse_algorithm',
            description=(
                'Parse and validate an algorithm string. '
                'Returns structured information about the moves.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': (
                            'Algorithm to parse '
                            "(e.g., 'R U R\\' U\\'')"
                        ),
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='analyze_algorithm',
            description=(
                'Comprehensive algorithm analysis: '
                'metrics (HTM/QTM/STM/ETM/RTM), '
                'ergonomics (comfort, execution time, finger usage), '
                'structure (conjugates, commutators, efficiency), '
                'impacts (pieces affected, patterns, complexity).'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': 'Algorithm to analyze',
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='inverse_algorithm',
            description=(
                'Get the inverse of an algorithm '
                '(reverses order and inverts each move).'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': 'Algorithm to invert',
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='simplify_algorithm',
            description=(
                'Optimize and simplify an algorithm by '
                'removing redundant moves, combining sequences (R R -> R2), '
                'and canceling inverses.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': 'Algorithm to simplify',
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='visualize_algorithm',
            description=(
                'Visualize the effect of an algorithm on a solved cube, '
                'showing which pieces are affected.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': 'Algorithm to visualize',
                    },
                    'orientation': {
                        'type': 'string',
                        'description': 'Cube orientation for display',
                        'default': '',
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='get_history',
            description='Get the move history of the current cube state.',
            inputSchema={
                'type': 'object',
                'properties': {},
            },
        ),
        Tool(
            name='set_state',
            description=(
                'Set the cube to a specific state '
                'using a 54-character facelet string.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'state': {
                        'type': 'string',
                        'description': (
                            '54-character facelet string '
                            'representing the cube state'
                        ),
                    },
                },
                'required': ['state'],
            },
        ),
    ]


def handle_apply_moves(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the apply_moves tool.

    Args:
        arguments: Tool arguments containing 'moves'.

    Returns:
        list[TextContent]: Result of applying moves.

    """
    cube = get_cube()
    moves = arguments['moves']

    algo = Algorithm.parse_moves(moves)
    cube.rotate(algo)

    display = cube.display()

    return [
        TextContent(
            type='text',
            text=(
                f'Applied moves: { algo }\n\n'
                f'Cube state:\n{ display }'
            ),
        ),
    ]


def handle_get_state(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the get_state tool.

    Args:
        arguments: Tool arguments with optional display, palette, orientation.

    Returns:
        list[TextContent]: Current cube state.

    """
    cube = get_cube()
    display_flag = arguments.get('display', True)
    palette = arguments.get('palette', 'default')
    orientation = arguments.get('orientation', '')

    result_state = f'State: { cube.state }\n'
    result_state += f'Solved: { cube.is_solved }\n'
    result_state += f'Orientation: { cube.orientation }\n'

    if display_flag:
        display = cube.display(palette=palette, orientation=orientation)
        result_state += f'\nVisualization:\n{ display }'

    return [
        TextContent(
            type='text',
            text=result_state,
        ),
    ]


def handle_reset_cube(arguments: dict[str, Any]) -> list[TextContent]:  # noqa: ARG001
    """
    Handle the reset_cube tool.

    Args:
        arguments: Tool arguments (unused).

    Returns:
        list[TextContent]: Result of resetting cube.

    """
    cube = reset_cube()
    return [
        TextContent(
            type='text',
            text=(
                f'Cube reset to solved state.\n\n'
                f'{ cube.display() }'
            ),
        ),
    ]


def handle_scramble_cube(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the scramble_cube tool.

    Args:
        arguments: Tool arguments containing optional 'length'.

    Returns:
        list[TextContent]: Result of scrambling cube.

    """
    cube = get_cube()
    length = arguments.get('length', 20)

    scramble_alg = scramble(3, length)
    cube.rotate(scramble_alg)

    return [
        TextContent(
            type='text',
            text=(
                f'Applied scramble: { scramble_alg }\n\n'
                f'{ cube.display() }'
            ),
        ),
    ]


def handle_is_solved(arguments: dict[str, Any]) -> list[TextContent]:  # noqa: ARG001
    """
    Handle the is_solved tool.

    Args:
        arguments: Tool arguments (unused).

    Returns:
        list[TextContent]: Whether cube is solved.

    """
    cube = get_cube()
    solved = cube.is_solved

    return [
        TextContent(
            type='text',
            text=f'Cube is { "solved" if solved else "not solved" }.',
        ),
    ]


def handle_parse_algorithm(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the parse_algorithm tool.

    Args:
        arguments: Tool arguments containing 'algorithm'.

    Returns:
        list[TextContent]: Parsed algorithm information.

    """
    algorithm = arguments['algorithm']

    algo = Algorithm.parse_moves(algorithm)

    moves_info = [
        {
            'move': str(move),
            'base': move.base_move,
            'modifier': move.modifier,
            'layer': move.layer,
            'is_wide': move.is_wide_move,
            'is_rotation': move.is_rotation_move,
        } for move in algo
    ]

    result_parse = {
        'algorithm': str(algo),
        'move_count': len(algo),
        'moves': moves_info,
    }

    return [
        TextContent(
            type='text',
            text=json.dumps(result_parse, indent=2),
        ),
    ]


def handle_analyze_algorithm(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the analyze_algorithm tool.

    Args:
        arguments: Tool arguments containing 'algorithm'.

    Returns:
        list[TextContent]: Algorithm analysis results.

    """
    algorithm = arguments['algorithm']

    algo = Algorithm.parse_moves(algorithm)
    metrics = algo.metrics
    ergonomics = algo.ergonomics
    structure = algo.structure
    impacts = algo.impacts

    result_analyze = {
        'algorithm': str(algo),
        'length': len(algo),
        'metrics': {
            'htm': metrics.htm,
            'qtm': metrics.qtm,
            'stm': metrics.stm,
            'etm': metrics.etm,
            'rtm': metrics.rtm,
            'qstm': metrics.qstm,
            'obtm': metrics.obtm,
            'obqtm': metrics.obqtm,
            'rbtm': metrics.rbtm,
            'btm': metrics.btm,
            'bqtm': metrics.bqtm,
            'pauses': metrics.pauses,
            'rotations': metrics.rotations,
            'outer_moves': metrics.outer_moves,
            'inner_moves': metrics.inner_moves,
            'generators': metrics.generators,
        },
        'ergonomics': {
            'comfort_score': ergonomics.comfort_score,
            'regrip_count': ergonomics.regrip_count,
            'hand_balance_ratio': ergonomics.hand_balance_ratio,
            'estimated_execution_time': ergonomics.estimated_execution_time,
            'ergonomic_rating': ergonomics.ergonomic_rating,
            'fingertrick_difficulty': ergonomics.fingertrick_difficulty,
            'awkward_moves': ergonomics.awkward_moves,
            'flow_breaks': ergonomics.flow_breaks,
            'right_hand_moves': ergonomics.right_hand_moves,
            'left_hand_moves': ergonomics.left_hand_moves,
            'both_hand_moves': ergonomics.both_hand_moves,
            'thumb_moves': ergonomics.thumb_moves,
            'index_finger_moves': ergonomics.index_finger_moves,
            'middle_finger_moves': ergonomics.middle_finger_moves,
            'ring_finger_moves': ergonomics.ring_finger_moves,
        },
        'structure': {
            'compressed': structure.compressed,
            'conjugate_count': structure.conjugate_count,
            'commutator_count': structure.commutator_count,
            'efficiency_rating': structure.efficiency_rating,
            'total_structures': structure.total_structures,
            'max_nesting_depth': structure.max_nesting_depth,
            'nested_structure_count': structure.nested_structure_count,
            'compression_ratio': structure.compression_ratio,
            'average_structure_score': structure.average_structure_score,
            'best_structure_score': structure.best_structure_score,
            'coverage_percent': structure.coverage_percent,
            'pure_commutator_count': structure.pure_commutator_count,
            'a9_commutator_count': structure.a9_commutator_count,
            'simple_conjugate_count': structure.simple_conjugate_count,
            'average_move_count': structure.average_move_count,
        },
        'impacts': {
            'mobilized_count': impacts.facelets_mobilized_count,
            'facelets_transformation_mask':
            impacts.facelets_transformation_mask,
            'facelets_scrambled_percent': impacts.facelets_scrambled_percent,
            'cubies_corners_moved': impacts.cubies_corners_moved,
            'cubies_corners_twisted': impacts.cubies_corners_twisted,
            'cubies_edges_moved': impacts.cubies_edges_moved,
            'cubies_edges_flipped': impacts.cubies_edges_flipped,
            'cubies_patterns': impacts.cubies_patterns,
            'cubies_complexity_score': impacts.cubies_complexity_score,
            'cubies_suggested_approach': impacts.cubies_suggested_approach,
        },
        'cycles': algo.cycles,
        'min_cube_size': algo.min_cube_size,
    }

    return [
        TextContent(
            type='text',
            text=json.dumps(result_analyze, indent=2),
        ),
    ]


def handle_visualize_algorithm(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the visualize_algorithm tool.

    Args:
        arguments: Tool arguments with 'algorithm' and optional 'orientation'.

    Returns:
        list[TextContent]: Algorithm visualization.

    """
    algorithm = arguments['algorithm']
    orientation = arguments.get('orientation', '')

    algo = Algorithm.parse_moves(algorithm)

    # Create a solved cube and apply the algorithm
    temp_cube = VCube()
    temp_cube.rotate(algo)

    # Get the impact mask
    mask = algo.impacts.facelets_transformation_mask

    display = temp_cube.display(orientation=orientation, mask=mask)

    result_visualize = f'Algorithm: { algo }\n'
    result_visualize += f'Moves: { len(algo) }\n'
    result_visualize += (
        'Affected pieces: '
        f'{ algo.impacts.facelets_mobilized_count }/54\n\n'
    )
    result_visualize += (
        'Visualization (affected pieces highlighted):\n'
        f'{ display }'
    )

    return [
        TextContent(
            type='text',
            text=result_visualize,
        ),
    ]


def handle_get_history(arguments: dict[str, Any]) -> list[TextContent]:  # noqa: ARG001
    """
    Handle the get_history tool.

    Args:
        arguments: Tool arguments (unused).

    Returns:
        list[TextContent]: Move history.

    """
    cube = get_cube()
    history = ' '.join(cube.history)

    return [
        TextContent(
            type='text',
            text=(
                f'Move history ({ len(cube.history) } moves):\n'
                f'{ history or "(empty)" }'
            ),
        ),
    ]


def handle_set_state(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the set_state tool.

    Args:
        arguments: Tool arguments containing 'state'.

    Returns:
        list[TextContent]: Result of setting state.

    """
    state = arguments['state']

    global _cube_state  # noqa: PLW0603
    _cube_state = VCube(state)

    return [
        TextContent(
            type='text',
            text=(
                f'Cube state set successfully.\n\n'
                f'{ _cube_state.display() }'
            ),
        ),
    ]


def handle_inverse_algorithm(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the inverse_algorithm tool.

    Args:
        arguments: Tool arguments containing 'algorithm'.

    Returns:
        list[TextContent]: Inverted algorithm.

    """
    algorithm = arguments['algorithm']

    algo = Algorithm.parse_moves(algorithm)
    inverted = mirror_moves(algo)

    return [
        TextContent(
            type='text',
            text=(
                f'Original: { algo }\n'
                f'Inverse: { inverted }'
            ),
        ),
    ]


def handle_simplify_algorithm(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle the simplify_algorithm tool.

    Args:
        arguments: Tool arguments containing 'algorithm'.

    Returns:
        list[TextContent]: Simplified algorithm.

    """
    algorithm = arguments['algorithm']

    algo = Algorithm.parse_moves(algorithm)
    simplified = compress_moves(algo)

    original_length = len(algo)
    simplified_length = len(simplified)
    reduction = original_length - simplified_length

    return [
        TextContent(
            type='text',
            text=(
                f'Original ({ original_length } moves): { algo }\n'
                f'Simplified ({ simplified_length } moves): { simplified }\n'
                f'Reduction: { reduction } move(s)'
            ),
        ),
    ]


@app.call_tool()
async def call_tool(  # noqa: RUF029
    name: str,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """
    Handle tool calls.

    Args:
        name: The name of the tool to call.
        arguments: The arguments for the tool.

    Returns:
        list[TextContent]: The result of the tool call.

    """
    handlers: dict[str, Any] = {
        'apply_moves': handle_apply_moves,
        'get_state': handle_get_state,
        'reset_cube': handle_reset_cube,
        'scramble_cube': handle_scramble_cube,
        'is_solved': handle_is_solved,
        'parse_algorithm': handle_parse_algorithm,
        'analyze_algorithm': handle_analyze_algorithm,
        'visualize_algorithm': handle_visualize_algorithm,
        'get_history': handle_get_history,
        'set_state': handle_set_state,
        'inverse_algorithm': handle_inverse_algorithm,
        'simplify_algorithm': handle_simplify_algorithm,
    }

    handler = handlers.get(name)
    if not handler:
        return [
            TextContent(
                type='text',
                text=f'Unknown tool: {name}',
            ),
        ]

    try:
        return handler(arguments)
    except Exception as e:  # noqa: BLE001
        return [
            TextContent(
                type='text',
                text=f'Error: {e!s}',
            ),
        ]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == '__main__':
    asyncio.run(main())

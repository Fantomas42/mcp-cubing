"""
MCP server for Rubik's cube manipulation and visualization.

This server provides tools for working with virtual Rubik's cubes,
including state management, move execution, visualization, and algorithm analysis.
"""

import json
from typing import Any

from cubing_algs import Algorithm
from cubing_algs import VCube
from cubing_algs.scrambler import scramble
from mcp.server import Server
from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

# Global cube state
_cube_state: VCube | None = None


def get_cube() -> VCube:
    """Get or initialize the global cube state."""
    global _cube_state
    if _cube_state is None:
        _cube_state = VCube()
    return _cube_state


def reset_cube() -> VCube:
    """Reset the cube to solved state."""
    global _cube_state
    _cube_state = VCube()
    return _cube_state


# Initialize MCP server
app = Server('mcp-cubing')


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available cube manipulation tools."""
    return [
        Tool(
            name='apply_moves',
            description='Apply a sequence of moves to the cube. Supports full WCA notation including wide moves (Rw, Lw), rotations (x, y, z), and slice moves (M, E, S). Also supports commutators [A, B] and conjugates [A: B].',
            inputSchema={
                'type': 'object',
                'properties': {
                    'moves': {
                        'type': 'string',
                        'description': "Move sequence in standard notation (e.g., 'R U R\\' U\\'', 'Rw U2 x', '[R, U]')",
                    },
                },
                'required': ['moves'],
            },
        ),
        Tool(
            name='get_state',
            description='Get the current cube state with optional visualization. Returns the 54-facelet state string and optional visual representation.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'display': {
                        'type': 'boolean',
                        'description': 'Whether to include visual representation (default: true)',
                        'default': True,
                    },
                    'palette': {
                        'type': 'string',
                        'description': "Color palette for display: 'default', 'pastel', 'bold', 'mono', etc.",
                        'default': 'default',
                    },
                    'orientation': {
                        'type': 'string',
                        'description': "Cube orientation (e.g., 'WG' for white top, green front)",
                        'default': '',
                    },
                },
            },
        ),
        Tool(
            name='reset_cube',
            description='Reset the cube to solved state (all faces with uniform colors).',
            inputSchema={
                'type': 'object',
                'properties': {},
            },
        ),
        Tool(
            name='scramble_cube',
            description='Apply a random scramble to the cube. Generates a random state scramble (RST) or random move scramble.',
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
            description='Parse and validate an algorithm string. Returns structured information about the moves.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'algorithm': {
                        'type': 'string',
                        'description': "Algorithm to parse (e.g., 'R U R\\' U\\'')",
                    },
                },
                'required': ['algorithm'],
            },
        ),
        Tool(
            name='analyze_algorithm',
            description='Analyze an algorithm and return comprehensive metrics including HTM/QTM counts, ergonomics, structure, and impact analysis.',
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
            name='visualize_algorithm',
            description='Visualize the effect of an algorithm on a solved cube, showing which pieces are affected.',
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
            description='Set the cube to a specific state using a 54-character facelet string.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'state': {
                        'type': 'string',
                        'description': '54-character facelet string representing the cube state',
                    },
                },
                'required': ['state'],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    if name == 'apply_moves':
        cube = get_cube()
        moves = arguments['moves']

        try:
            algo = Algorithm.parse_moves(moves)
            cube.rotate(algo)

            display = cube.display()

            return [
                TextContent(
                    type='text',
                    text=f'Applied moves: {algo}\n\nCube state:\n{display}',
                ),
            ]
        except Exception as e:
            return [
                TextContent(
                    type='text',
                    text=f'Error applying moves: {e!s}',
                ),
            ]

    elif name == 'get_state':
        cube = get_cube()
        display_flag = arguments.get('display', True)
        palette = arguments.get('palette', 'default')
        orientation = arguments.get('orientation', '')

        result = f'State: {cube.state}\n'
        result += f'Solved: {cube.is_solved}\n'
        result += f'Orientation: {cube.orientation}\n'

        if display_flag:
            result += f'\nVisualization:\n{cube.display(palette=palette, orientation=orientation)}'

        return [
            TextContent(
                type='text',
                text=result,
            ),
        ]

    elif name == 'reset_cube':
        cube = reset_cube()
        return [
            TextContent(
                type='text',
                text=f'Cube reset to solved state.\n\n{cube.display()}',
            ),
        ]

    elif name == 'scramble_cube':
        cube = get_cube()
        length = arguments.get('length', 20)

        scramble_alg = scramble(length)
        cube.rotate(scramble_alg)

        return [
            TextContent(
                type='text',
                text=f'Applied scramble: {scramble_alg}\n\n{cube.display()}',
            ),
        ]

    elif name == 'is_solved':
        cube = get_cube()
        solved = cube.is_solved

        return [
            TextContent(
                type='text',
                text=f"Cube is {'solved' if solved else 'not solved'}.",
            ),
        ]

    elif name == 'parse_algorithm':
        algorithm = arguments['algorithm']

        try:
            algo = Algorithm.parse_moves(algorithm)

            moves_info = []
            for move in algo:
                moves_info.append({
                    'move': str(move),
                    'base': move.base_move,
                    'modifier': move.modifier,
                    'layer': move.layer,
                    'is_wide': move.is_wide_move,
                    'is_rotation': move.is_rotation_move,
                })

            result = {
                'algorithm': str(algo),
                'move_count': len(algo),
                'moves': moves_info,
            }

            return [
                TextContent(
                    type='text',
                    text=json.dumps(result, indent=2),
                ),
            ]
        except Exception as e:
            return [
                TextContent(
                    type='text',
                    text=f'Error parsing algorithm: {e!s}',
                ),
            ]

    elif name == 'analyze_algorithm':
        algorithm = arguments['algorithm']

        try:
            algo = Algorithm.parse_moves(algorithm)
            metrics = algo.metrics
            ergonomics = algo.ergonomics
            structure = algo.structure
            impacts = algo.impacts

            result = {
                'algorithm': str(algo),
                'metrics': {
                    'htm': metrics.htm,
                    'qtm': metrics.qtm,
                    'stm': metrics.stm,
                    'etm': metrics.etm,
                    'generators': metrics.generators,
                },
                'ergonomics': {
                    'comfort_score': ergonomics.comfort_score,
                    'regrip_count': ergonomics.regrip_count,
                    'hand_balance_ratio': ergonomics.hand_balance_ratio,
                },
                'structure': {
                    'compressed': structure.compressed,
                    'conjugate_count': structure.conjugate_count,
                    'commutator_count': structure.commutator_count,
                },
                'impacts': {
                    'mobilized_count': impacts.facelets_mobilized_count,
                    'facelets_transformation_mask': impacts.facelets_transformation_mask,
                },
                'cycles': algo.cycles,
                'min_cube_size': algo.min_cube_size,
            }

            return [
                TextContent(
                    type='text',
                    text=json.dumps(result, indent=2),
                ),
            ]
        except Exception as e:
            return [
                TextContent(
                    type='text',
                    text=f'Error analyzing algorithm: {e!s}',
                ),
            ]

    elif name == 'visualize_algorithm':
        algorithm = arguments['algorithm']
        orientation = arguments.get('orientation', '')

        try:
            algo = Algorithm.parse_moves(algorithm)

            # Create a solved cube and apply the algorithm
            temp_cube = VCube()
            temp_cube.rotate(algo)

            # Get the impact mask
            mask = algo.impacts.facelets_transformation_mask

            display = temp_cube.display(orientation=orientation, mask=mask)

            result = f'Algorithm: {algo}\n'
            result += f'Moves: {len(algo)}\n'
            result += f'Affected pieces: {algo.impacts.facelets_mobilized_count}/54\n\n'
            result += f'Visualization (affected pieces highlighted):\n{display}'

            return [
                TextContent(
                    type='text',
                    text=result,
                ),
            ]
        except Exception as e:
            return [
                TextContent(
                    type='text',
                    text=f'Error visualizing algorithm: {e!s}',
                ),
            ]

    elif name == 'get_history':
        cube = get_cube()
        history = ' '.join(cube.history)

        return [
            TextContent(
                type='text',
                text=f"Move history ({len(cube.history)} moves):\n{history or '(empty)'}",
            ),
        ]

    elif name == 'set_state':
        state = arguments['state']

        try:
            global _cube_state
            _cube_state = VCube(state)

            return [
                TextContent(
                    type='text',
                    text=f'Cube state set successfully.\n\n{_cube_state.display()}',
                ),
            ]
        except Exception as e:
            return [
                TextContent(
                    type='text',
                    text=f'Error setting state: {e!s}',
                ),
            ]

    else:
        return [
            TextContent(
                type='text',
                text=f'Unknown tool: {name}',
            ),
        ]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

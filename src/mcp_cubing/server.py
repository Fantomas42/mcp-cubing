"""
MCP server for Rubik's cube manipulation and visualization.

This server provides tools for working with virtual Rubik's cubes,
including state management, move execution, visualization,
and algorithm analysis.
"""

# ruff: noqa: RUF029, TRY300, UP042
import json
from enum import Enum

from cubing_algs.algorithm import Algorithm
from cubing_algs.scrambler import scramble
from cubing_algs.transform.mirror import mirror_moves
from cubing_algs.transform.size import compress_moves
from cubing_algs.vcube import VCube
from kociemba import solve  # type: ignore[import-untyped]
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

# ============================================================================
# Constants
# ============================================================================

# VCube only supports 3x3x3 cubes
SUPPORTED_CUBE_SIZE = 3

# Maximum response size in characters (MCP best practice)
CHARACTER_LIMIT = 25000

# ============================================================================
# Global Cube State
# ============================================================================
# IMPORTANT: The server maintains a single global cube state that persists
# across tool calls within an MCP session. This is critical to understand:
# - get_cube() returns or initializes the global cube
# - reset_cube() resets global state to solved
# - All apply_moves, scramble_cube, and set_state operations mutate this
#   global state
# - Each MCP connection gets its own isolated cube state (not shared across
#   sessions)
# ============================================================================

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


def set_cube_state(state: str) -> VCube:
    """
    Set the global cube to a specific state.

    Args:
        state: 54-character facelet string.

    Returns:
        VCube: The cube with new state.

    """
    global _cube_state  # noqa: PLW0603

    _cube_state = VCube(state)
    return _cube_state


# ============================================================================
# Enums
# ============================================================================


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = 'markdown'
    JSON = 'json'


# ============================================================================
# Pydantic Input Models
# ============================================================================


class ApplyMovesInput(BaseModel):
    """Input model for applying moves to the cube."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    moves: str = Field(
        ...,
        description=(
            "Move sequence in standard notation. Supports full WCA notation "
            "including wide moves (Rw, Lw), rotations (x, y, z), slice moves "
            "(M, E, S), commutators [A, B], and conjugates [A: B]. "
            "Examples: \"R U R' U'\", \"Rw U2 x\", \"[R, U]\""
        ),
        min_length=1,
        max_length=1000,
    )

    @field_validator('moves')
    @classmethod
    def validate_moves(cls, v: str) -> str:
        """
        Validate moves string is not empty.

        Returns:
            str: The validated and stripped moves string.

        Raises:
            ValueError: If moves string is empty or whitespace only.

        """
        if not v.strip():
            msg = 'Moves cannot be empty or whitespace only'
            raise ValueError(msg)
        return v.strip()


class GetStateInput(BaseModel):
    """Input model for getting cube state."""

    model_config = ConfigDict(
        validate_assignment=True,
    )

    display: bool = Field(
        default=True,
        description='Whether to include visual representation (default: true)',
    )
    palette: str = Field(
        default='default',
        description=(
            "Color palette for display: 'default', 'pastel', 'dracula', "
            "'colorblind', 'bold', 'mono', etc."
        ),
    )
    orientation: str = Field(
        default='',
        description=(
            "Cube orientation as 2-character string. First character is top "
            "face, second is front face. Examples: 'UF' (white top, green "
            "front), 'RD' (red top, yellow front). Leave empty for default."
        ),
        max_length=2,
    )


class ScrambleCubeInput(BaseModel):
    """Input model for scrambling the cube."""

    model_config = ConfigDict(
        validate_assignment=True,
    )

    cube_size: int = Field(
        default=3,
        description=(
            'Size of the cube (e.g., 3 for 3x3x3, 4 for 4x4x4, 5 for 5x5x5). '
            'Note: VCube only supports 3x3x3, so non-3 sizes will generate '
            'the scramble without applying it to the global cube.'
        ),
        ge=2,
        le=7,
    )
    iterations: int = Field(
        default=0,
        description=(
            'Number of random moves (0 for automatic length based on cube '
            'size: 20 for 3x3x3, 40 for 4x4x4, 60 for 5x5x5)'
        ),
        ge=0,
        le=200,
    )
    inner_layers: bool = Field(
        default=False,
        description=(
            'Whether to include inner layer moves for larger cubes '
            '(e.g., 2R, 3Rw for 4x4x4+)'
        ),
    )
    right_handed: bool = Field(
        default=True,
        description=(
            'Whether to optimize scramble for right-handed solving '
            '(fewer awkward moves)'
        ),
    )


class AlgorithmInput(BaseModel):
    """Input model for algorithm operations (parse, analyze, etc.)."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    algorithm: str = Field(
        ...,
        description=(
            "Algorithm to process in standard notation. Examples: "
            "\"R U R' U'\", \"F R U R' U' F'\", \"[R, U]\""
        ),
        min_length=1,
        max_length=1000,
    )

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """
        Validate algorithm string is not empty.

        Returns:
            str: The validated and stripped algorithm string.

        Raises:
            ValueError: If algorithm string is empty or whitespace only.

        """
        if not v.strip():
            msg = 'Algorithm cannot be empty or whitespace only'
            raise ValueError(msg)
        return v.strip()


class AnalyzeAlgorithmInput(BaseModel):
    """Input model for algorithm analysis with response format option."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    algorithm: str = Field(
        ...,
        description='Algorithm to analyze in standard notation',
        min_length=1,
        max_length=1000,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description=(
            "Output format: 'json' for structured machine-readable data "
            "(default), 'markdown' for human-readable formatted text"
        ),
    )

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """
        Validate algorithm string is not empty.

        Returns:
            str: The validated and stripped algorithm string.

        Raises:
            ValueError: If algorithm string is empty or whitespace only.

        """
        if not v.strip():
            msg = 'Algorithm cannot be empty or whitespace only'
            raise ValueError(msg)
        return v.strip()


class VisualizeAlgorithmInput(BaseModel):
    """Input model for algorithm visualization."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    algorithm: str = Field(
        ...,
        description='Algorithm to visualize',
        min_length=1,
        max_length=1000,
    )
    orientation: str = Field(
        default='',
        description='Cube orientation for display (2-char string like "UF")',
        max_length=2,
    )

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """
        Validate algorithm string is not empty.

        Returns:
            str: The validated and stripped algorithm string.

        Raises:
            ValueError: If algorithm string is empty or whitespace only.

        """
        if not v.strip():
            msg = 'Algorithm cannot be empty or whitespace only'
            raise ValueError(msg)
        return v.strip()


class SetStateInput(BaseModel):
    """Input model for setting cube state."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    state: str = Field(
        ...,
        description=(
            '54-character facelet string representing the cube state. '
            'Order: U face (9), R face (9), F face (9), D face (9), '
            'L face (9), B face (9). Each face is top-left to bottom-right. '
            'Example solved state: '
            '"UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"'
        ),
        min_length=54,
        max_length=54,
    )

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """
        Validate state string is exactly 54 characters.

        Returns:
            str: The validated and stripped state string.

        Raises:
            ValueError: If state string is not exactly 54 characters.

        """
        if len(v) != 54:  # noqa: PLR2004
            msg = f'State must be exactly 54 characters, got {len(v)}'
            raise ValueError(msg)
        return v.strip()


# ============================================================================
# Helper Functions
# ============================================================================


def _handle_error(e: Exception) -> str:
    """
    Format error messages consistently across all tools.

    Args:
        e: The exception to format.

    Returns:
        str: Formatted error message with guidance.

    """
    error_message = str(e)

    # Parse algorithm errors
    if 'Invalid' in error_message or 'parse' in error_message.lower():
        return (
            f'Error: Invalid algorithm notation. {error_message}\n\n'
            "Supported notation: U, D, L, R, F, B with modifiers ', 2; "
            'Wide moves (Rw, Lw); Rotations (x, y, z); Slice moves (M, E, S); '
            'Commutators [A, B]; Conjugates [A: B]'
        )

    # Cube state errors
    if 'state' in error_message.lower() or '54' in error_message:
        return (
            f'Error: Invalid cube state. {error_message}\n\n'
            'State must be a 54-character string representing all facelets. '
            'Use cubing_get_state to see the current state format.'
        )

    # Generic error with the original message
    return f'Error: {error_message}'


def _check_character_limit(text: str) -> str:
    """
    Check if response exceeds CHARACTER_LIMIT and truncate if needed.

    Args:
        text: The response text to check.

    Returns:
        str: Original text or truncated text with message.

    """
    if len(text) <= CHARACTER_LIMIT:
        return text

    truncation_point = CHARACTER_LIMIT - 200
    truncated = text[:truncation_point]

    return (
        f'{truncated}\n\n'
        f'[Response truncated at {CHARACTER_LIMIT} characters]\n'
        f'The full output was {len(text)} characters. '
        f'For large results, consider using filters or pagination parameters.'
    )


def _format_analysis_markdown(result: dict) -> str:
    """
    Format algorithm analysis as human-readable markdown.

    Args:
        result: The analysis result dictionary.

    Returns:
        str: Markdown-formatted analysis.

    """
    metrics = result['metrics']
    ergonomics = result['ergonomics']
    structure = result['structure']
    impacts = result['impacts']

    lines = [
        f"# Algorithm Analysis: {result['algorithm']}",
        '',
        f'**Length:** {result["length"]} moves',
        (
            f'**Min Cube Size:** '
            f'{result["min_cube_size"]}x{result["min_cube_size"]}'
        ),
        '',
        '## Metrics',
        f'- **HTM** (Half Turn Metric): {metrics["htm"]}',
        f'- **QTM** (Quarter Turn Metric): {metrics["qtm"]}',
        f'- **STM** (Slice Turn Metric): {metrics["stm"]}',
        f'- **ETM** (Execution Turn Metric): {metrics["etm"]}',
        f'- **RTM** (Regrip Turn Metric): {metrics["rtm"]}',
        f'- **Rotations:** {metrics["rotations"]}',
        f'- **Outer Moves:** {metrics["outer_moves"]}',
        f'- **Inner Moves:** {metrics["inner_moves"]}',
        '',
        '## Ergonomics',
        f'- **Comfort Score:** {ergonomics["comfort_score"]:.2f}',
        f'- **Ergonomic Rating:** {ergonomics["ergonomic_rating"]}',
        f'- **Execution Time:** ~{ergonomics["estimated_execution_time"]:.2f}s',
        f'- **Regrip Count:** {ergonomics["regrip_count"]}',
        f'- **Hand Balance:** {ergonomics["hand_balance_ratio"]:.2f}',
        f'- **Fingertrick Difficulty:** {ergonomics["fingertrick_difficulty"]}',
        f'- **Flow Breaks:** {ergonomics["flow_breaks"]}',
        '',
        '### Finger Usage',
        f'- Right hand: {ergonomics["right_hand_moves"]} moves',
        f'- Left hand: {ergonomics["left_hand_moves"]} moves',
        f'- Both hands: {ergonomics["both_hand_moves"]} moves',
        f'- Thumb: {ergonomics["thumb_moves"]}',
        f'- Index: {ergonomics["index_finger_moves"]}',
        f'- Middle: {ergonomics["middle_finger_moves"]}',
        f'- Ring: {ergonomics["ring_finger_moves"]}',
        '',
        '## Structure',
        f'- **Compressed Form:** {structure["compressed"]}',
        f'- **Efficiency Rating:** {structure["efficiency_rating"]}',
        f'- **Compression Ratio:** {structure["compression_ratio"]:.2f}',
        f'- **Conjugates:** {structure["conjugate_count"]} '
        f'({structure["simple_conjugate_count"]} simple)',
        f'- **Commutators:** {structure["commutator_count"]} '
        f'({structure["pure_commutator_count"]} pure, '
        f'{structure["a9_commutator_count"]} A9)',
        f'- **Nesting Depth:** {structure["max_nesting_depth"]}',
        f'- **Coverage:** {structure["coverage_percent"]:.1f}%',
        '',
        '## Impact',
        (
            f'- **Affected Pieces:** {impacts["mobilized_count"]}/54 '
            f'facelets ({impacts["facelets_scrambled_percent"]:.1f}%)'
        ),
        f'- **Corners Moved:** {impacts["cubies_corners_moved"]}',
        f'- **Corners Twisted:** {impacts["cubies_corners_twisted"]}',
        f'- **Edges Moved:** {impacts["cubies_edges_moved"]}',
        f'- **Edges Flipped:** {impacts["cubies_edges_flipped"]}',
        f'- **Complexity Score:** {impacts["cubies_complexity_score"]:.2f}',
        f'- **Suggested Approach:** {impacts["cubies_suggested_approach"]}',
    ]

    # Add patterns if present
    if impacts['cubies_patterns']:
        lines.extend(['', '### Patterns Detected'])
        lines.extend(f'- {pattern}' for pattern in impacts['cubies_patterns'])

    # Add cycles information
    if result.get('cycles'):
        lines.extend(['', '## Cycle Notation', f'```\n{result["cycles"]}\n```'])

    return '\n'.join(lines)


# ============================================================================
# Initialize FastMCP Server
# ============================================================================

mcp = FastMCP('mcp-cubing')

# ============================================================================
# Tool Implementations
# ============================================================================


@mcp.tool(
    name='cubing_apply_moves',
    annotations={
        'title': 'Apply Moves to Cube',
        'readOnlyHint': False,
        'destructiveHint': False,
        'idempotentHint': False,
        'openWorldHint': False,
    },
)
async def cubing_apply_moves(params: ApplyMovesInput) -> list[TextContent]:
    """
    Apply a sequence of moves to the global cube state.

    This tool modifies the persistent global cube by applying the
    specified move sequence. It supports full WCA notation including wide
    moves, rotations, slice moves, commutators, and conjugates.

    Args:
        params (ApplyMovesInput): Validated input containing:
            - moves (str): Move sequence in standard notation

    Returns:
        list[TextContent]: Applied moves and current cube visualization

    Examples:
        - Use when: "Apply R U R' U' to the cube"
        - Use when: "Execute the sexy move"
        - Use when: "Apply commutator [R, U]"
        - Don't use when: Just analyzing an algorithm
          (use cubing_analyze_algorithm)
        - Don't use when: Visualizing without modifying state
          (use cubing_visualize_algorithm)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors
        - Provides guidance on supported notation
        - Shows which part of the move sequence failed

    """
    try:
        cube = get_cube()
        algo = Algorithm.parse_moves(params.moves)
        cube.rotate(algo)

        display = cube.display()

        return [TextContent(
            type='text',
            text=f'Applied moves: {algo}\n\nCube state:\n{display}',
        )]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_get_state',
    annotations={
        'title': 'Get Current Cube State',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_get_state(params: GetStateInput) -> list[TextContent]:
    """
    Get the current state of the global cube with optional visualization.

    Returns the 54-facelet state string and optionally a visual representation.
    This tool is read-only and does not modify the cube state.

    Args:
        params (GetStateInput): Validated input containing:
            - display (bool): Include visual representation (default: true)
            - palette (str): Color palette for display (default: 'default')
            - orientation (str): Cube orientation like 'UF' (default: '')

    Returns:
        list[TextContent]: Current state, solved status, and optional
            visualization

    Examples:
        - Use when: "Show me the current cube"
        - Use when: "What's the cube state?"
        - Use when: "Display the cube with pastel colors"
        - Don't use when: You want to modify the cube (use cubing_apply_moves)

    Error Handling:
        - Always succeeds (returns current state)
        - Invalid palette falls back to default

    """
    try:
        cube = get_cube()

        result = f'State: {cube.state}\n'
        result += f'Solved: {cube.is_solved}\n'
        result += f'Orientation: {cube.orientation}\n'

        if params.display:
            display = cube.display(
                palette=params.palette,
                orientation=params.orientation,
            )
            result += f'\nVisualization:\n{display}'

        return [TextContent(type='text', text=result)]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_reset_cube',
    annotations={
        'title': 'Reset Cube to Solved',
        'readOnlyHint': False,
        'destructiveHint': True,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_reset_cube() -> list[TextContent]:
    """
    Reset the global cube to solved state.

    This is a destructive operation that discards all moves and returns the
    cube to its initial solved state. The operation is idempotent - calling
    it multiple times has the same effect as calling it once.

    Returns:
        list[TextContent]: Confirmation message with solved cube visualization

    Examples:
        - Use when: "Reset the cube"
        - Use when: "Start with a solved cube"
        - Use when: "Clear all moves"
        - Don't use when: You want to undo the last move (no undo feature yet)

    Error Handling:
        - Always succeeds (creates new solved cube)

    """
    try:
        cube = reset_cube()
        return [TextContent(
            type='text',
            text=f'Cube reset to solved state.\n\n{cube.display()}',
        )]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_scramble_cube',
    annotations={
        'title': 'Scramble Cube',
        'readOnlyHint': False,
        'destructiveHint': False,
        'idempotentHint': False,
        'openWorldHint': False,
    },
)
async def cubing_scramble_cube(params: ScrambleCubeInput) -> list[TextContent]:
    """
    Apply a random scramble to the cube.

    Generates and optionally applies a random move sequence to scramble the
    cube. For 3x3x3 cubes, applies to the global state. For other sizes,
    only generates the scramble (VCube only supports 3x3x3).

    Args:
        params (ScrambleCubeInput): Validated input containing:
            - cube_size (int): Cube size 2-7 (default: 3)
            - iterations (int): Number of moves, 0 for auto (default: 0)
            - inner_layers (bool): Include inner moves (default: false)
            - right_handed (bool): Optimize for right-hand (default: true)

    Returns:
        list[TextContent]: Generated scramble and cube state or just scramble

    Examples:
        - Use when: "Scramble the cube"
        - Use when: "Generate a 4x4x4 scramble"
        - Use when: "Give me a 25-move scramble"
        - Don't use when: You want a specific pattern (use cubing_apply_moves)

    Error Handling:
        - Returns error for invalid cube size
        - Falls back to automatic length for iterations=0

    """
    try:
        scramble_alg = scramble(
            params.cube_size,
            params.iterations,
            inner_layers=params.inner_layers,
            right_handed=params.right_handed,
        )

        # Only apply to global VCube if cube_size is 3
        if params.cube_size == SUPPORTED_CUBE_SIZE:
            cube = get_cube()
            cube.rotate(scramble_alg)

            return [TextContent(
                type='text',
                text=f'Applied scramble: {scramble_alg}\n\n{cube.display()}',
            )]

        # For other cube sizes, just return the scramble
        return [TextContent(
            type='text',
            text=(
                f'Generated {params.cube_size}x{params.cube_size}x'
                f'{params.cube_size} scramble:\n'
                f'{scramble_alg}\n\n'
                f'Note: VCube only supports 3x3x3 cubes, so the scramble was '
                f'not applied to the global cube state.'
            ),
        )]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_is_solved',
    annotations={
        'title': 'Check if Cube is Solved',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_is_solved() -> str:
    """
    Check if the global cube is currently in a solved state.

    Returns a simple yes/no answer about whether the cube is solved (all
    faces have uniform colors). This is a read-only check.

    Returns:
        str: "Cube is solved." or "Cube is not solved."

    Examples:
        - Use when: "Is the cube solved?"
        - Use when: "Check if I'm done"
        - Don't use when: You want to see the state (use cubing_get_state)
        - Don't use when: You want to solve it (use cubing_solve_cube)

    Error Handling:
        - Always succeeds (checks internal state)

    """
    try:
        cube = get_cube()
        solved = cube.is_solved

        return f'Cube is {"solved" if solved else "not solved"}.'

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_parse_algorithm',
    annotations={
        'title': 'Parse Algorithm',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_parse_algorithm(params: AlgorithmInput) -> str:
    """
    Parse and validate an algorithm string into structured move information.

    Parses the algorithm and returns detailed information about each move
    including base move, modifiers, layers, and move types. Does not modify
    the cube state.

    Args:
        params (AlgorithmInput): Validated input containing:
            - algorithm (str): Algorithm to parse

    Returns:
        str: JSON-formatted move breakdown with details for each move

    Examples:
        - Use when: "Parse the algorithm R U R' U'"
        - Use when: "Break down this move sequence"
        - Use when: "Validate this algorithm notation"
        - Don't use when: You want analysis (use cubing_analyze_algorithm)
        - Don't use when: You want to apply it (use cubing_apply_moves)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors
        - Shows which part of the algorithm failed parsing

    """
    try:
        algo = Algorithm.parse_moves(params.algorithm)

        moves_info = [
            {
                'move': str(move),
                'base': move.base_move,
                'modifier': move.modifier,
                'layer': move.layer,
                'is_wide': move.is_wide_move,
                'is_rotation': move.is_rotation_move,
            }
            for move in algo
        ]

        result = {
            'algorithm': str(algo),
            'move_count': len(algo),
            'moves': moves_info,
        }

        return json.dumps(result, indent=2)

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_analyze_algorithm',
    annotations={
        'title': 'Analyze Algorithm',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_analyze_algorithm(params: AnalyzeAlgorithmInput) -> str:
    """
    Perform comprehensive analysis of a cube algorithm.

    Analyzes an algorithm and returns detailed metrics including move counts
    (HTM/QTM/STM/ETM), ergonomics (comfort, execution time, finger usage),
    structure (conjugates, commutators, efficiency), and impact (pieces
    affected, patterns, complexity). Does not modify the cube state.

    Args:
        params (AnalyzeAlgorithmInput): Validated input containing:
            - algorithm (str): Algorithm to analyze
            - response_format (ResponseFormat): 'json' or 'markdown'
              (default: json)

    Returns:
        str: Comprehensive analysis in requested format (JSON or Markdown)

    Examples:
        - Use when: "Analyze this F2L algorithm: R U R' U'"
        - Use when: "What are the metrics for this sequence?"
        - Use when: "How ergonomic is this algorithm?"
        - Use when: "Give me detailed algorithm analysis"
        - Don't use when: Just parsing (use cubing_parse_algorithm)
        - Don't use when: Visualizing effect (use cubing_visualize_algorithm)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors
        - Provides guidance on supported notation

    """
    try:
        algo = Algorithm.parse_moves(params.algorithm)
        metrics = algo.metrics
        ergonomics = algo.ergonomics
        structure = algo.structure
        impacts = algo.impacts

        result = {
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
                'facelets_scrambled_percent':
                    impacts.facelets_scrambled_percent,
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

        # Format based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            output = _format_analysis_markdown(result)
        else:
            output = json.dumps(result, indent=2)

        return _check_character_limit(output)

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_mirror_algorithm',
    annotations={
        'title': 'Mirror Algorithm',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_mirror_algorithm(params: AlgorithmInput) -> str:
    """
    Get the mirror (inverse) of an algorithm.

    Returns the mirror of the algorithm by reversing the order and inverting
    each move. The mirror undoes what the original algorithm does. Does not
    modify the cube state.

    Args:
        params (AlgorithmInput): Validated input containing:
            - algorithm (str): Algorithm to mirror

    Returns:
        str: Original and mirrored algorithm strings

    Examples:
        - Use when: "What's the inverse of R U R' U'?"
        - Use when: "Mirror this algorithm"
        - Use when: "How do I undo these moves?"
        - Don't use when: You want to simplify (use cubing_simplify_algorithm)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors

    """
    try:
        algo = Algorithm.parse_moves(params.algorithm)
        mirrored = mirror_moves(algo)

        return f'Original: {algo}\nMirrored: {mirrored}'

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_simplify_algorithm',
    annotations={
        'title': 'Simplify Algorithm',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_simplify_algorithm(params: AlgorithmInput) -> str:
    """
    Optimize and simplify an algorithm by removing redundant moves.

    Simplifies the algorithm by combining sequences (R R → R2), canceling
    inverses (R R' → <nothing>), and removing redundant moves
    (R2 R2 → <nothing>). The simplified algorithm has the same effect as
    the original. Does not modify the cube state.

    Args:
        params (AlgorithmInput): Validated input containing:
            - algorithm (str): Algorithm to simplify

    Returns:
        str: Original and simplified algorithms with move reduction count

    Examples:
        - Use when: "Simplify R U R U"
        - Use when: "Optimize this move sequence"
        - Use when: "Compress this algorithm"
        - Don't use when: You want the inverse (use cubing_mirror_algorithm)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors

    """
    try:
        algo = Algorithm.parse_moves(params.algorithm)
        simplified = compress_moves(algo)

        original_length = len(algo)
        simplified_length = len(simplified)
        reduction = original_length - simplified_length

        return (
            f'Original ({original_length} moves): {algo}\n'
            f'Simplified ({simplified_length} moves): {simplified}\n'
            f'Reduction: {reduction} move(s)'
        )

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_visualize_algorithm',
    annotations={
        'title': 'Visualize Algorithm Effect',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_visualize_algorithm(
    params: VisualizeAlgorithmInput,
) -> list[TextContent]:
    """
    Visualize the effect of an algorithm on a solved cube.

    Shows which pieces are affected by applying the algorithm to a solved
    cube. Affected pieces are highlighted in the visualization. This is a
    read-only operation that does not modify the global cube state.

    Args:
        params (VisualizeAlgorithmInput): Validated input containing:
            - algorithm (str): Algorithm to visualize
            - orientation (str): Cube orientation for display (default: '')

    Returns:
        list[TextContent]: Algorithm info and visualization with affected pieces

    Examples:
        - Use when: "Show me what R U R' U' affects"
        - Use when: "Visualize the effect of this algorithm"
        - Use when: "Which pieces does this move?"
        - Don't use when: You want to apply it (use cubing_apply_moves)
        - Don't use when: You want metrics (use cubing_analyze_algorithm)

    Error Handling:
        - Returns "Error: Invalid algorithm notation" for parse errors

    """
    try:
        algo = Algorithm.parse_moves(params.algorithm)

        # Create a temporary solved cube and apply the algorithm
        temp_cube = VCube()
        temp_cube.rotate(algo)

        # Get the impact mask
        mask = algo.impacts.facelets_transformation_mask

        display = temp_cube.display(
            orientation=params.orientation,
            mask=mask,
        )

        result = f'Algorithm: {algo}\n'
        result += f'Moves: {len(algo)}\n'
        result += (
            f'Affected pieces: '
            f'{algo.impacts.facelets_mobilized_count}/54\n\n'
        )
        result += f'Visualization (affected pieces highlighted):\n{display}'

        return [TextContent(type='text', text=result)]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_get_history',
    annotations={
        'title': 'Get Move History',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_get_history() -> str:
    """
    Get the move history of the current global cube state.

    Returns the complete sequence of moves that have been applied to the cube
    since it was last reset. This is a read-only operation.

    Returns:
        str: Move count and complete move history

    Examples:
        - Use when: "Show me what moves I've done"
        - Use when: "What's the move history?"
        - Use when: "How did I get to this state?"
        - Don't use when: You want to see the cube state (use cubing_get_state)

    Error Handling:
        - Always succeeds (returns empty history if none)

    """
    try:
        cube = get_cube()
        history = ' '.join(cube.history)

        result = f'Move history ({len(cube.history)} moves):\n'
        result += history or '(empty)'

        return result

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


@mcp.tool(
    name='cubing_set_state',
    annotations={
        'title': 'Set Cube State',
        'readOnlyHint': False,
        'destructiveHint': True,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_set_state(params: SetStateInput) -> list[TextContent]:
    """
    Set the global cube to a specific state using a 54-character facelet string.

    This is a destructive operation that replaces the current cube state with
    the specified state. The state string represents all 54 facelets in a
    specific order.

    Args:
        params (SetStateInput): Validated input containing:
            - state (str): 54-character facelet string

    Returns:
        list[TextContent]: Confirmation message with new cube visualization

    Examples:
        - Use when: "Set the cube to this state: UUUUUU..."
        - Use when: "Load a specific cube configuration"
        - Don't use when: You want to apply moves (use cubing_apply_moves)
        - Don't use when: You want to reset (use cubing_reset_cube)

    Error Handling:
        - Returns "Error: Invalid cube state" if string is not 54 characters
        - Returns error if state is invalid/unsolvable

    """
    try:
        cube = set_cube_state(params.state)

        return [TextContent(
            type='text',
            text=f'Cube state set successfully.\n\n{cube.display()}',
        )]

    except Exception as e:  # noqa: BLE001
        return [TextContent(type='text', text=_handle_error(e))]


@mcp.tool(
    name='cubing_solve_cube',
    annotations={
        'title': 'Solve Cube',
        'readOnlyHint': True,
        'destructiveHint': False,
        'idempotentHint': True,
        'openWorldHint': False,
    },
)
async def cubing_solve_cube() -> str:
    """
    Find a solution for the current cube state using Kociemba algorithm.

    Calculates an optimal or near-optimal solution for the current cube state.
    Typically returns solutions in 20 moves or less. This is a read-only
    operation that does not modify the cube state - it only returns the
    solution algorithm.

    Returns:
        str: Solution algorithm and move count, or "already solved" message

    Examples:
        - Use when: "Solve the cube"
        - Use when: "Find a solution"
        - Use when: "How do I solve this?"
        - Don't use when: Cube is already solved (returns immediate message)
        - Don't use when: You want to apply moves
          (use cubing_apply_moves with the solution)

    Error Handling:
        - Returns error if cube state is invalid/unsolvable
        - Returns "Cube is already solved!" if no solution needed

    """
    try:
        cube = get_cube()

        # Check if already solved
        if cube.is_solved:
            return 'Cube is already solved!'

        solution = Algorithm.parse_moves(solve(cube.state))

        return f'Solution: {solution}\nMoves: {len(solution)}'

    except Exception as e:  # noqa: BLE001
        return _handle_error(e)


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Run the MCP server using FastMCP."""
    mcp.run()


if __name__ == '__main__':
    main()

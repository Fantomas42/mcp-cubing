# MCP Cubing Server

An MCP (Model Context Protocol) server for Rubik's cube manipulation and visualization.

This server provides comprehensive tools for working with virtual Rubik's cubes, perfect for developing and testing cube-related projects.

## Features

- **Cube State Management**: Maintain and manipulate a persistent virtual cube
- **Full Notation Support**: All WCA notations including wide moves (Rw), rotations (x, y, z), slice moves (M, E, S)
- **Advanced Notation**: Commutators `[A, B]` and conjugates `[A: B]`
- **Visualization**: Terminal-based cube visualization with multiple color palettes
- **Algorithm Analysis**: Comprehensive metrics including HTM/QTM, ergonomics, structure analysis
- **Scrambling**: Random state and move-based scrambling

## Installation

```bash
# Install from source
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Available Tools

All tools are prefixed with `cubing_` to avoid naming conflicts with other MCP servers.

### `cubing_apply_moves`
Apply a sequence of moves to the cube.

**Parameters:**
- `moves` (string): Move sequence in standard notation

**Examples:**
```
R U R' U'
Rw U2 x
[R, U]  # Commutator
[F: R U R' U']  # Conjugate
```

### `cubing_get_state`
Get the current cube state with optional visualization.

**Parameters:**
- `display` (boolean, optional): Include visual representation (default: true)
- `palette` (string, optional): Color palette ('default', 'pastel', 'dracula', 'colorblind', etc.)
- `orientation` (string, optional): Cube orientation (2-char string like 'UF')

### `cubing_reset_cube`
Reset the cube to solved state. (Destructive operation)

### `cubing_scramble_cube`
Apply a random scramble to the cube.

**Parameters:**
- `cube_size` (integer, optional): Cube size 2-7 (default: 3)
- `iterations` (integer, optional): Number of moves, 0 for auto (default: 0)
- `inner_layers` (boolean, optional): Include inner layer moves (default: false)
- `right_handed` (boolean, optional): Optimize for right-handed (default: true)

### `cubing_is_solved`
Check if the cube is currently solved.

### `cubing_parse_algorithm`
Parse and validate an algorithm string, returning structured move information.

**Parameters:**
- `algorithm` (string): Algorithm to parse

### `cubing_analyze_algorithm`
Perform comprehensive algorithm analysis.

**Parameters:**
- `algorithm` (string): Algorithm to analyze
- `response_format` (string, optional): 'json' or 'markdown' (default: 'json')

**Returns:**
- HTM/QTM/STM/ETM/RTM metrics
- Ergonomics (comfort score, regrip count, hand balance, execution time, finger usage)
- Structure (conjugates, commutators, compression, efficiency)
- Impact analysis (affected pieces, patterns, complexity, suggested approach)
- Algorithm cycles and minimum cube size

### `cubing_mirror_algorithm`
Get the mirror (inverse) of an algorithm.

**Parameters:**
- `algorithm` (string): Algorithm to mirror

### `cubing_simplify_algorithm`
Optimize and simplify an algorithm by removing redundant moves.

**Parameters:**
- `algorithm` (string): Algorithm to simplify

### `cubing_visualize_algorithm`
Visualize the effect of an algorithm on a solved cube.

**Parameters:**
- `algorithm` (string): Algorithm to visualize
- `orientation` (string, optional): Display orientation

### `cubing_get_history`
Get the move history of the current cube state.

### `cubing_set_state`
Set the cube to a specific state using a 54-character facelet string. (Destructive)

**Parameters:**
- `state` (string): 54-character facelet string

### `cubing_solve_cube`
Find a solution for the current cube state using the Kociemba algorithm.

## Usage with Claude Code

Add this to your .mcp.json file

```json
{
  "mcpServers": {
    "cube": {
      "command": "python",
      "args": ["-m", "mcp_cubing"],
      "cwd": "/somewhere/mcp-cubing"
    }
  }
}
```

For development with local cubing-algs:

```json
{
  "mcpServers": {
    "cube": {
      "command": "python",
      "args": ["-m", "mcp_cubing"],
      "cwd": "/somewhere/mcp-cubing",
      "env": {
        "PYTHONPATH": "/somewhere/cubing-algs"
      }
    }
  }
}
```

## Example Interactions

### Basic Cube Manipulation
```
User: Apply the sexy move to the cube
Assistant: *uses cubing_apply_moves with "R U R' U'"*

User: Is it solved?
Assistant: *uses cubing_is_solved*

User: Reset it
Assistant: *uses cubing_reset_cube*
```

### Algorithm Development
```
User: I'm working on a new OLL algorithm: F R U R' U' F'. Can you analyze it?
Assistant: *uses cubing_analyze_algorithm*
- HTM: 6 moves
- Ergonomics: Good comfort score
- Structure: Conjugate detected [F: R U R' U']
- Affects: 20/54 pieces
```

### Algorithm Comparison
```
User: Compare these two F2L algorithms
Assistant:
*uses cubing_analyze_algorithm for both*
*compares metrics, ergonomics, and structure*
```

## What's New in v0.2.0

**FastMCP Migration:** The server has been modernized using FastMCP with significant improvements:

- **Automatic Input Validation:** All inputs are validated using Pydantic models with field constraints
- **Tool Annotations:** All tools now have proper annotations (readOnlyHint, destructiveHint, etc.)
- **Tool Name Prefix:** All tools are prefixed with `cubing_` to prevent naming conflicts
- **Response Format Options:** Analysis tools support both JSON and Markdown output formats
- **Improved Error Messages:** Better, more actionable error messages with guidance
- **Character Limits:** Built-in response truncation for large outputs
- **Comprehensive Docstrings:** Enhanced documentation with usage examples and error handling details
- **Code Quality:** 40% reduction in codebase size with better maintainability

## Development

The server uses the `cubing-algs` library which provides:
- `VCube`: Virtual cube state management
- `Algorithm`: Move sequence representation
- `Move`: Individual move parsing and validation
- Comprehensive analysis tools

## Supported Notations

- **Basic moves**: U, D, L, R, F, B
- **Modifiers**: ' (prime), 2 (double)
- **Wide moves**: Rw, Lw, Uw, Dw, Fw, Bw (or SiGN: r, l, u, d, f, b)
- **Rotations**: x, y, z
- **Slice moves**: M, E, S
- **Layered moves**: 2R, 3Rw, 3-4Rw
- **Commutators**: [A, B] → A B A' B'
- **Conjugates**: [A: B] → A B A'

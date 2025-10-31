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

### `apply_moves`
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

### `get_state`
Get the current cube state with optional visualization.

**Parameters:**
- `display` (boolean, optional): Include visual representation (default: true)
- `palette` (string, optional): Color palette ('default', 'pastel', 'bold', 'mono')
- `orientation` (string, optional): Cube orientation (e.g., 'WG' for white top, green front)

### `reset_cube`
Reset the cube to solved state.

### `scramble_cube`
Apply a random scramble to the cube.

**Parameters:**
- `length` (integer, optional): Number of random moves (default: 20)

### `is_solved`
Check if the cube is currently solved.

### `parse_algorithm`
Parse and validate an algorithm string, returning structured move information.

**Parameters:**
- `algorithm` (string): Algorithm to parse

### `analyze_algorithm`
Perform comprehensive algorithm analysis.

**Parameters:**
- `algorithm` (string): Algorithm to analyze

**Returns:**
- HTM/QTM/STM/ETM metrics
- Ergonomics (comfort score, regrip count, hand balance)
- Structure (conjugates, commutators, compression)
- Impact analysis (affected pieces)
- Algorithm cycles

### `visualize_algorithm`
Visualize the effect of an algorithm on a solved cube.

**Parameters:**
- `algorithm` (string): Algorithm to visualize
- `orientation` (string, optional): Display orientation

### `get_history`
Get the move history of the current cube state.

### `set_state`
Set the cube to a specific state using a 54-character facelet string.

**Parameters:**
- `state` (string): 54-character facelet string

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
Assistant: *uses apply_moves with "R U R' U'"*

User: Is it solved?
Assistant: *uses is_solved*

User: Reset it
Assistant: *uses reset_cube*
```

### Algorithm Development
```
User: I'm working on a new OLL algorithm: F R U R' U' F'. Can you analyze it?
Assistant: *uses analyze_algorithm*
- HTM: 6 moves
- Ergonomics: Good comfort score
- Structure: Conjugate detected [F: R U R' U']
- Affects: 20/54 pieces
```

### Algorithm Comparison
```
User: Compare these two F2L algorithms
Assistant:
*uses analyze_algorithm for both*
*compares metrics, ergonomics, and structure*
```

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

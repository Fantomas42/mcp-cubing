# MCP Cubing Server - Usage Examples

## Tool Reference

### apply_moves
Apply moves to the persistent cube state.

```json
{
  "moves": "R U R' U'"
}
```

### get_state
Get current cube state with optional visualization.

```json
{
  "display": true,
  "palette": "default",
  "orientation": ""
}
```

### reset_cube
Reset cube to solved state. No parameters.

### scramble_cube
Generate random scramble.

```json
{
  "length": 20
}
```

### is_solved
Check if cube is solved. No parameters.

### parse_algorithm
Parse algorithm string into structured format.

```json
{
  "algorithm": "R U R' U'"
}
```

### analyze_algorithm
Comprehensive algorithm analysis.

```json
{
  "algorithm": "F R U R' U' F'"
}
```

### visualize_algorithm
Show algorithm effect on solved cube with highlighting.

```json
{
  "algorithm": "R U R' U R U2 R'",
  "orientation": ""
}
```

### get_history
Get move history of current cube. No parameters.

### set_state
Set cube to specific state.

```json
{
  "state": "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
}
```

## Use Case Examples

### 1. Algorithm Development

**Scenario:** Developing a new F2L algorithm

```
User: I'm working on a front-right F2L case. Let me try this: R U R' U' R U R'
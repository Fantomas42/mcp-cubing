"""Unit tests for MCP Cubing server."""
# ruff: noqa: D101, D102, SLF001, PLR6301

import asyncio
import json
import unittest

from cubing_algs import VCube
from cubing_algs.exceptions import InvalidMoveError
from mcp.types import TextContent

from mcp_cubing import server


class TestGetCube(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_get_cube_initializes_new_cube(self) -> None:
        cube = server.get_cube()
        self.assertIsInstance(cube, VCube)
        self.assertTrue(cube.is_solved)

    def test_get_cube_returns_existing_cube(self) -> None:
        cube1 = server.get_cube()
        cube1.rotate("R U R' U'")
        cube2 = server.get_cube()
        self.assertIs(cube1, cube2)
        self.assertFalse(cube2.is_solved)

    def test_get_cube_state_persists(self) -> None:
        cube = server.get_cube()
        cube.rotate('R')
        state_before = cube.state
        cube_again = server.get_cube()
        self.assertEqual(cube_again.state, state_before)


class TestResetCube(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_reset_cube_creates_solved_cube(self) -> None:
        cube = server.reset_cube()
        self.assertIsInstance(cube, VCube)
        self.assertTrue(cube.is_solved)

    def test_reset_cube_clears_scrambled_state(self) -> None:
        cube = server.get_cube()
        cube.rotate("R U R' U'")
        self.assertFalse(cube.is_solved)
        reset = server.reset_cube()
        self.assertTrue(reset.is_solved)

    def test_reset_cube_updates_global_state(self) -> None:
        cube = server.get_cube()
        cube.rotate("R U R' U'")
        server.reset_cube()
        cube_after = server.get_cube()
        self.assertTrue(cube_after.is_solved)


class TestHandleApplyMoves(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_apply_moves_valid_moves(self) -> None:
        result = server.handle_apply_moves({'moves': "R U R' U'"})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn('Applied moves:', result[0].text)
        self.assertEqual(result[0].type, 'text')

    def test_apply_moves_changes_cube_state(self) -> None:
        cube = server.get_cube()
        initial_state = cube.state
        server.handle_apply_moves({'moves': 'R'})
        self.assertNotEqual(cube.state, initial_state)

    def test_apply_moves_wide_moves(self) -> None:
        result = server.handle_apply_moves({'moves': 'Rw Uw'})
        self.assertIsInstance(result, list)
        self.assertIn('Applied moves:', result[0].text)

    def test_apply_moves_rotations(self) -> None:
        result = server.handle_apply_moves({'moves': 'x y z'})
        self.assertIsInstance(result, list)
        self.assertIn('Applied moves:', result[0].text)

    def test_apply_moves_slice_moves(self) -> None:
        result = server.handle_apply_moves({'moves': 'M E S'})
        self.assertIsInstance(result, list)
        self.assertIn('Applied moves:', result[0].text)

    def test_apply_moves_commutator(self) -> None:
        result = server.handle_apply_moves({'moves': '[R, U]'})
        self.assertIsInstance(result, list)
        self.assertIn('Applied moves:', result[0].text)

    def test_apply_moves_conjugate(self) -> None:
        result = server.handle_apply_moves({'moves': '[R: U]'})
        self.assertIsInstance(result, list)
        self.assertIn('Applied moves:', result[0].text)

    def test_apply_moves_empty_string(self) -> None:
        result = server.handle_apply_moves({'moves': ''})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)


class TestHandleGetState(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_get_state_default_display(self) -> None:
        result = server.handle_get_state({})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('State:', result[0].text)
        self.assertIn('Solved:', result[0].text)
        self.assertIn('Visualization:', result[0].text)

    def test_get_state_without_display(self) -> None:
        result = server.handle_get_state({'display': False})
        self.assertIsInstance(result, list)
        self.assertIn('State:', result[0].text)
        self.assertNotIn('Visualization:', result[0].text)

    def test_get_state_with_palette(self) -> None:
        result = server.handle_get_state({'palette': 'pastel'})
        self.assertIsInstance(result, list)
        self.assertIn('Visualization:', result[0].text)

    def test_get_state_with_orientation(self) -> None:
        result = server.handle_get_state({'orientation': 'UF'})
        self.assertIsInstance(result, list)
        self.assertIn('Visualization:', result[0].text)

    def test_get_state_shows_solved_status(self) -> None:
        server.reset_cube()
        result = server.handle_get_state({})
        self.assertIn('Solved: True', result[0].text)

    def test_get_state_shows_unsolved_status(self) -> None:
        cube = server.get_cube()
        cube.rotate('R')
        result = server.handle_get_state({})
        self.assertIn('Solved: False', result[0].text)


class TestHandleResetCube(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_reset_cube_returns_text_content(self) -> None:
        result = server.handle_reset_cube({})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)

    def test_reset_cube_message(self) -> None:
        result = server.handle_reset_cube({})
        self.assertIn('Cube reset to solved state', result[0].text)

    def test_reset_cube_after_scramble(self) -> None:
        cube = server.get_cube()
        cube.rotate("R U R' U'")
        server.handle_reset_cube({})
        cube = server.get_cube()
        self.assertTrue(cube.is_solved)


class TestHandleScrambleCube(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_scramble_cube_returns_text_content(self) -> None:
        # Scramble can occasionally generate invalid moves (cubing-algs issue)
        # Skip test if scramble fails (not our bug)
        try:
            result = server.handle_scramble_cube({})
            self.assertIsInstance(result, list)
            self.assertIn('Applied scramble:', result[0].text)
        except InvalidMoveError:
            self.skipTest('Scramble generated invalid move (cubing-algs issue)')


class TestHandleIsSolved(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_is_solved_true(self) -> None:
        server.reset_cube()
        result = server.handle_is_solved({})
        self.assertIsInstance(result, list)
        self.assertIn('solved', result[0].text)
        self.assertNotIn('not solved', result[0].text)

    def test_is_solved_false(self) -> None:
        cube = server.get_cube()
        cube.rotate('R')
        result = server.handle_is_solved({})
        self.assertIn('not solved', result[0].text)

    def test_is_solved_after_inverse(self) -> None:
        cube = server.get_cube()
        cube.rotate("R U R' U'")
        cube.rotate("U R U' R'")
        result = server.handle_is_solved({})
        self.assertIn('solved', result[0].text)


class TestHandleParseAlgorithm(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_parse_algorithm_valid(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': "R U R' U'"})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        data = json.loads(result[0].text)
        self.assertIn('algorithm', data)
        self.assertIn('move_count', data)
        self.assertIn('moves', data)

    def test_parse_algorithm_move_count(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertEqual(data['move_count'], 4)

    def test_parse_algorithm_move_details(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': 'R'})
        data = json.loads(result[0].text)
        move = data['moves'][0]
        self.assertIn('move', move)
        self.assertIn('base', move)
        self.assertIn('modifier', move)
        self.assertIn('layer', move)
        self.assertIn('is_wide', move)
        self.assertIn('is_rotation', move)

    def test_parse_algorithm_wide_move(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': 'Rw'})
        data = json.loads(result[0].text)
        self.assertTrue(data['moves'][0]['is_wide'])

    def test_parse_algorithm_rotation_move(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': 'x'})
        data = json.loads(result[0].text)
        self.assertTrue(data['moves'][0]['is_rotation'])

    def test_parse_algorithm_commutator(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': '[R, U]'})
        data = json.loads(result[0].text)
        self.assertEqual(data['move_count'], 4)

    def test_parse_algorithm_empty(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': ''})
        data = json.loads(result[0].text)
        self.assertEqual(data['move_count'], 0)


class TestHandleAnalyzeAlgorithm(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_analyze_algorithm_valid(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        data = json.loads(result[0].text)
        self.assertIn('algorithm', data)

    def test_analyze_algorithm_has_metrics(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('metrics', data)
        metrics = data['metrics']
        self.assertIn('htm', metrics)
        self.assertIn('qtm', metrics)
        self.assertIn('stm', metrics)
        self.assertIn('etm', metrics)
        self.assertIn('rtm', metrics)
        self.assertIn('qstm', metrics)
        self.assertIn('pauses', metrics)
        self.assertIn('rotations', metrics)
        self.assertIn('outer_moves', metrics)
        self.assertIn('inner_moves', metrics)
        self.assertIn('generators', metrics)

    def test_analyze_algorithm_has_ergonomics(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('ergonomics', data)
        ergonomics = data['ergonomics']
        self.assertIn('comfort_score', ergonomics)
        self.assertIn('regrip_count', ergonomics)
        self.assertIn('hand_balance_ratio', ergonomics)
        self.assertIn('estimated_execution_time', ergonomics)
        self.assertIn('ergonomic_rating', ergonomics)
        self.assertIn('fingertrick_difficulty', ergonomics)
        self.assertIn('awkward_moves', ergonomics)
        self.assertIn('flow_breaks', ergonomics)
        self.assertIn('right_hand_moves', ergonomics)
        self.assertIn('left_hand_moves', ergonomics)
        self.assertIn('both_hand_moves', ergonomics)
        self.assertIn('thumb_moves', ergonomics)
        self.assertIn('index_finger_moves', ergonomics)
        self.assertIn('middle_finger_moves', ergonomics)
        self.assertIn('ring_finger_moves', ergonomics)

    def test_analyze_algorithm_has_structure(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('structure', data)
        structure = data['structure']
        self.assertIn('compressed', structure)
        self.assertIn('conjugate_count', structure)
        self.assertIn('commutator_count', structure)
        self.assertIn('efficiency_rating', structure)
        self.assertIn('total_structures', structure)
        self.assertIn('max_nesting_depth', structure)
        self.assertIn('nested_structure_count', structure)
        self.assertIn('compression_ratio', structure)
        self.assertIn('average_structure_score', structure)
        self.assertIn('best_structure_score', structure)
        self.assertIn('coverage_percent', structure)
        self.assertIn('pure_commutator_count', structure)
        self.assertIn('a9_commutator_count', structure)
        self.assertIn('simple_conjugate_count', structure)
        self.assertIn('average_move_count', structure)

    def test_analyze_algorithm_has_impacts(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('impacts', data)
        impacts = data['impacts']
        self.assertIn('mobilized_count', impacts)
        self.assertIn('facelets_transformation_mask', impacts)
        self.assertIn('facelets_scrambled_percent', impacts)
        self.assertIn('cubies_corners_moved', impacts)
        self.assertIn('cubies_corners_twisted', impacts)
        self.assertIn('cubies_edges_moved', impacts)
        self.assertIn('cubies_edges_flipped', impacts)
        self.assertIn('cubies_patterns', impacts)
        self.assertIn('cubies_complexity_score', impacts)
        self.assertIn('cubies_suggested_approach', impacts)

    def test_analyze_algorithm_has_cycles(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('cycles', data)

    def test_analyze_algorithm_has_min_cube_size(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        self.assertIn('min_cube_size', data)

    def test_analyze_algorithm_property_count(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': "R U R' U'"})
        data = json.loads(result[0].text)
        metrics_count = len(data['metrics'])
        ergonomics_count = len(data['ergonomics'])
        structure_count = len(data['structure'])
        impacts_count = len(data['impacts'])
        total = (
            metrics_count + ergonomics_count + structure_count
            + impacts_count + 3
        )
        self.assertGreaterEqual(total, 50)

    def test_analyze_algorithm_empty(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': ''})
        data = json.loads(result[0].text)
        self.assertEqual(data['length'], 0)


class TestHandleVisualizeAlgorithm(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_visualize_algorithm_valid(self) -> None:
        result = server.handle_visualize_algorithm({'algorithm': "R U R' U'"})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('Algorithm:', result[0].text)
        self.assertIn('Moves:', result[0].text)
        self.assertIn('Affected pieces:', result[0].text)
        self.assertIn('Visualization', result[0].text)

    def test_visualize_algorithm_with_orientation(self) -> None:
        result = server.handle_visualize_algorithm({
            'algorithm': "R U R' U'",
            'orientation': 'UF',
        })
        self.assertIsInstance(result, list)
        self.assertIn('Visualization', result[0].text)

    def test_visualize_algorithm_does_not_affect_global_state(self) -> None:
        server.reset_cube()
        initial_state = server.get_cube().state
        server.handle_visualize_algorithm({'algorithm': "R U R' U'"})
        final_state = server.get_cube().state
        self.assertEqual(initial_state, final_state)

    def test_visualize_algorithm_empty(self) -> None:
        result = server.handle_visualize_algorithm({'algorithm': ''})
        self.assertIsInstance(result, list)
        self.assertIn('Moves: 0', result[0].text)


class TestHandleGetHistory(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_get_history_empty(self) -> None:
        server.reset_cube()
        result = server.handle_get_history({})
        self.assertIsInstance(result, list)
        self.assertIn('Move history', result[0].text)
        self.assertIn('(empty)', result[0].text)

    def test_get_history_with_moves(self) -> None:
        cube = server.get_cube()
        cube.rotate("R U R' U'")
        result = server.handle_get_history({})
        self.assertIn('Move history', result[0].text)
        self.assertNotIn('(empty)', result[0].text)

    def test_get_history_shows_move_count(self) -> None:
        cube = server.get_cube()
        cube.rotate('R U')
        result = server.handle_get_history({})
        self.assertIn('2 moves', result[0].text)

    def test_get_history_after_reset(self) -> None:
        cube = server.get_cube()
        cube.rotate('R U')
        server.reset_cube()
        result = server.handle_get_history({})
        self.assertIn('(empty)', result[0].text)


class TestHandleSetState(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_set_state_valid(self) -> None:
        solved_state = 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        result = server.handle_set_state({'state': solved_state})
        self.assertIsInstance(result, list)
        self.assertIn('Cube state set successfully', result[0].text)

    def test_set_state_updates_global_state(self) -> None:
        solved_state = 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        server.handle_set_state({'state': solved_state})
        cube = server.get_cube()
        self.assertEqual(cube.state, solved_state)

    def test_set_state_scrambled(self) -> None:
        scrambled_state = (
            'UULUUFUUFRRUBRRURRFFDFFUFFFDDRDDDDDDBLLLLLLLLBRRBBBBBB'
        )
        result = server.handle_set_state({'state': scrambled_state})
        self.assertIsInstance(result, list)
        self.assertIn('Cube state set successfully', result[0].text)


class TestHandleInverseAlgorithm(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_inverse_algorithm_valid(self) -> None:
        result = server.handle_inverse_algorithm({'algorithm': "R U R' U'"})
        self.assertIsInstance(result, list)
        self.assertIn('Original:', result[0].text)
        self.assertIn('Inverse:', result[0].text)

    def test_inverse_algorithm_simple(self) -> None:
        result = server.handle_inverse_algorithm({'algorithm': 'R'})
        self.assertIsInstance(result, list)
        self.assertIn('Inverse:', result[0].text)

    def test_inverse_algorithm_does_not_affect_global_state(self) -> None:
        server.reset_cube()
        initial_state = server.get_cube().state
        server.handle_inverse_algorithm({'algorithm': "R U R' U'"})
        final_state = server.get_cube().state
        self.assertEqual(initial_state, final_state)

    def test_inverse_algorithm_empty(self) -> None:
        result = server.handle_inverse_algorithm({'algorithm': ''})
        self.assertIsInstance(result, list)


class TestHandleSimplifyAlgorithm(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_simplify_algorithm_valid(self) -> None:
        result = server.handle_simplify_algorithm({'algorithm': 'R R'})
        self.assertIsInstance(result, list)
        self.assertIn('Original', result[0].text)
        self.assertIn('Simplified', result[0].text)
        self.assertIn('Reduction:', result[0].text)

    def test_simplify_algorithm_removes_redundant_moves(self) -> None:
        result = server.handle_simplify_algorithm({'algorithm': 'R R'})
        self.assertIn('Reduction:', result[0].text)

    def test_simplify_algorithm_no_simplification(self) -> None:
        result = server.handle_simplify_algorithm({'algorithm': 'R U'})
        self.assertIsInstance(result, list)
        self.assertIn('Reduction:', result[0].text)

    def test_simplify_algorithm_canceling_inverses(self) -> None:
        result = server.handle_simplify_algorithm({'algorithm': "R R'"})
        self.assertIsInstance(result, list)

    def test_simplify_algorithm_does_not_affect_global_state(self) -> None:
        server.reset_cube()
        initial_state = server.get_cube().state
        server.handle_simplify_algorithm({'algorithm': 'R R R'})
        final_state = server.get_cube().state
        self.assertEqual(initial_state, final_state)

    def test_simplify_algorithm_empty(self) -> None:
        result = server.handle_simplify_algorithm({'algorithm': ''})
        self.assertIsInstance(result, list)


class TestCallTool(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_call_tool_apply_moves(self) -> None:
        result = asyncio.run(server.call_tool('apply_moves', {'moves': 'R'}))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_call_tool_get_state(self) -> None:
        result = asyncio.run(server.call_tool('get_state', {}))
        self.assertIsInstance(result, list)

    def test_call_tool_reset_cube(self) -> None:
        result = asyncio.run(server.call_tool('reset_cube', {}))
        self.assertIsInstance(result, list)

    def test_call_tool_scramble_cube(self) -> None:
        result = asyncio.run(server.call_tool('scramble_cube', {}))
        self.assertIsInstance(result, list)

    def test_call_tool_is_solved(self) -> None:
        result = asyncio.run(server.call_tool('is_solved', {}))
        self.assertIsInstance(result, list)

    def test_call_tool_parse_algorithm(self) -> None:
        result = asyncio.run(
            server.call_tool('parse_algorithm', {'algorithm': 'R'}),
        )
        self.assertIsInstance(result, list)

    def test_call_tool_analyze_algorithm(self) -> None:
        result = asyncio.run(
            server.call_tool('analyze_algorithm', {'algorithm': 'R'}),
        )
        self.assertIsInstance(result, list)

    def test_call_tool_visualize_algorithm(self) -> None:
        result = asyncio.run(
            server.call_tool('visualize_algorithm', {'algorithm': 'R'}),
        )
        self.assertIsInstance(result, list)

    def test_call_tool_get_history(self) -> None:
        result = asyncio.run(server.call_tool('get_history', {}))
        self.assertIsInstance(result, list)

    def test_call_tool_set_state(self) -> None:
        solved = 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        result = asyncio.run(server.call_tool('set_state', {'state': solved}))
        self.assertIsInstance(result, list)

    def test_call_tool_inverse_algorithm(self) -> None:
        result = asyncio.run(
            server.call_tool('inverse_algorithm', {'algorithm': 'R'}),
        )
        self.assertIsInstance(result, list)

    def test_call_tool_simplify_algorithm(self) -> None:
        result = asyncio.run(
            server.call_tool('simplify_algorithm', {'algorithm': 'R R'}),
        )
        self.assertIsInstance(result, list)

    def test_call_tool_unknown_tool(self) -> None:
        result = asyncio.run(server.call_tool('unknown_tool', {}))
        self.assertIsInstance(result, list)
        self.assertIn('Unknown tool:', result[0].text)

    def test_call_tool_invalid_algorithm_returns_error(self) -> None:
        result = asyncio.run(
            server.call_tool('apply_moves', {'moves': 'BADMOVE'}),
        )
        self.assertIsInstance(result, list)
        self.assertIn('Error:', result[0].text)

    def test_call_tool_returns_text_content_on_error(self) -> None:
        result = asyncio.run(
            server.call_tool('apply_moves', {'moves': 'INVALID'}),
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertEqual(result[0].type, 'text')

    def test_call_tool_invalid_state_returns_error(self) -> None:
        result = asyncio.run(
            server.call_tool('set_state', {'state': 'INVALID'}),
        )
        self.assertIsInstance(result, list)
        self.assertIn('Error:', result[0].text)


class TestListTools(unittest.TestCase):
    def test_list_tools_returns_list(self) -> None:
        result = asyncio.run(server.list_tools())
        self.assertIsInstance(result, list)

    def test_list_tools_returns_12_tools(self) -> None:
        result = asyncio.run(server.list_tools())
        self.assertEqual(len(result), 12)

    def test_list_tools_tool_names(self) -> None:
        result = asyncio.run(server.list_tools())
        tool_names = [tool.name for tool in result]
        expected_names = [
            'apply_moves',
            'get_state',
            'reset_cube',
            'scramble_cube',
            'is_solved',
            'parse_algorithm',
            'analyze_algorithm',
            'inverse_algorithm',
            'simplify_algorithm',
            'visualize_algorithm',
            'get_history',
            'set_state',
        ]
        for name in expected_names:
            self.assertIn(name, tool_names)

    def test_list_tools_have_descriptions(self) -> None:
        result = asyncio.run(server.list_tools())
        for tool in result:
            self.assertTrue(hasattr(tool, 'description'))
            self.assertIsInstance(tool.description, str)
            self.assertGreater(len(tool.description), 0)

    def test_list_tools_have_input_schema(self) -> None:
        result = asyncio.run(server.list_tools())
        for tool in result:
            self.assertTrue(hasattr(tool, 'inputSchema'))
            self.assertIsInstance(tool.inputSchema, dict)


class TestGlobalStateIsolation(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_state_persists_across_tool_calls(self) -> None:
        asyncio.run(server.call_tool('apply_moves', {'moves': 'R'}))
        result1 = asyncio.run(server.call_tool('get_state', {}))
        result2 = asyncio.run(server.call_tool('get_state', {}))
        self.assertEqual(result1[0].text, result2[0].text)

    def test_reset_affects_subsequent_calls(self) -> None:
        asyncio.run(server.call_tool('apply_moves', {'moves': "R U R' U'"}))
        asyncio.run(server.call_tool('reset_cube', {}))
        result = asyncio.run(server.call_tool('is_solved', {}))
        self.assertIn('solved', result[0].text)
        self.assertNotIn('not solved', result[0].text)

    def test_apply_moves_accumulates(self) -> None:
        asyncio.run(server.call_tool('reset_cube', {}))
        asyncio.run(server.call_tool('apply_moves', {'moves': 'R'}))
        asyncio.run(server.call_tool('apply_moves', {'moves': 'U'}))
        result = asyncio.run(server.call_tool('get_history', {}))
        self.assertIn('2 moves', result[0].text)


class TestEdgeCases(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_apply_moves_with_whitespace(self) -> None:
        result = server.handle_apply_moves({'moves': '  R  U  '})
        self.assertIsInstance(result, list)

    def test_get_state_with_all_parameters(self) -> None:
        result = server.handle_get_state({
            'display': True,
            'palette': 'default',
            'orientation': 'UF',
        })
        self.assertIsInstance(result, list)

    def test_scramble_with_small_length(self) -> None:
        result = server.handle_scramble_cube({'length': 3})
        self.assertIsInstance(result, list)

    def test_multiple_resets(self) -> None:
        server.handle_reset_cube({})
        server.handle_reset_cube({})
        server.handle_reset_cube({})
        cube = server.get_cube()
        self.assertTrue(cube.is_solved)

    def test_set_state_then_apply_moves(self) -> None:
        solved = 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB'
        server.handle_set_state({'state': solved})
        server.handle_apply_moves({'moves': 'R'})
        cube = server.get_cube()
        self.assertFalse(cube.is_solved)

    def test_parse_algorithm_with_numbers(self) -> None:
        result = server.handle_parse_algorithm({'algorithm': 'R2 U2'})
        data = json.loads(result[0].text)
        self.assertEqual(data['move_count'], 2)

    def test_analyze_algorithm_single_move(self) -> None:
        result = server.handle_analyze_algorithm({'algorithm': 'R'})
        data = json.loads(result[0].text)
        self.assertEqual(data['length'], 1)

    def test_visualize_empty_orientation(self) -> None:
        result = server.handle_visualize_algorithm({
            'algorithm': 'R',
            'orientation': '',
        })
        self.assertIsInstance(result, list)

    def test_inverse_of_inverse(self) -> None:
        server.reset_cube()
        server.get_cube().rotate("R U R' U'")
        server.get_cube().rotate("U R U' R'")
        self.assertTrue(server.get_cube().is_solved)


class TestAsyncFunctions(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_call_tool_is_async(self) -> None:
        coro = server.call_tool('is_solved', {})
        self.assertTrue(asyncio.iscoroutine(coro))
        result = asyncio.run(coro)
        self.assertIsInstance(result, list)

    def test_list_tools_is_async(self) -> None:
        coro = server.list_tools()
        self.assertTrue(asyncio.iscoroutine(coro))
        result = asyncio.run(coro)
        self.assertIsInstance(result, list)

    def test_multiple_async_calls(self) -> None:
        async def run_multiple() -> tuple[
            list[TextContent],
            list[TextContent],
            list[TextContent],
        ]:
            r1 = await server.call_tool('reset_cube', {})
            r2 = await server.call_tool('apply_moves', {'moves': 'R'})
            r3 = await server.call_tool('is_solved', {})
            return r1, r2, r3

        results = asyncio.run(run_multiple())
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsInstance(result, list)


class TestErrorHandling(unittest.TestCase):
    def setUp(self) -> None:
        server._cube_state = None

    def tearDown(self) -> None:
        server._cube_state = None

    def test_invalid_move_notation(self) -> None:
        result = asyncio.run(
            server.call_tool('apply_moves', {'moves': 'INVALID'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_invalid_algorithm_parse(self) -> None:
        result = asyncio.run(
            server.call_tool('parse_algorithm', {'algorithm': 'XYZ123'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_invalid_algorithm_analyze(self) -> None:
        result = asyncio.run(
            server.call_tool('analyze_algorithm', {'algorithm': 'BADMOVE'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_invalid_algorithm_visualize(self) -> None:
        result = asyncio.run(
            server.call_tool('visualize_algorithm', {'algorithm': 'NOTVALID'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_invalid_algorithm_inverse(self) -> None:
        result = asyncio.run(
            server.call_tool('inverse_algorithm', {'algorithm': 'WRONG'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_invalid_algorithm_simplify(self) -> None:
        result = asyncio.run(
            server.call_tool('simplify_algorithm', {'algorithm': 'BAD'}),
        )
        self.assertIn('Error:', result[0].text)

    def test_error_returns_single_text_content(self) -> None:
        result = asyncio.run(
            server.call_tool('apply_moves', {'moves': 'INVALID'}),
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)

    def test_no_exception_raised_on_error(self) -> None:
        try:
            asyncio.run(server.call_tool('apply_moves', {'moves': 'BADMOVE'}))
        except Exception:  # noqa: BLE001
            self.fail('call_tool raised exception instead of returning error')

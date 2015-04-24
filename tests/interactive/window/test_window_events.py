"""
Tests for events on windows.
"""

import random

from pyglet import font
from pyglet import gl
from pyglet.window import key, Window

from tests.interactive.interactive_test_base import InteractiveTestCase, requires_user_action


class WindowEventsTestCase(InteractiveTestCase):
    """
    Base class that shows a window displaying instructions for the test. Then it waits for events
    to continue. Optionally the user can fail the test by pressing Escape.
    """

    # Defaults
    window_size = 400, 200
    window = None
    question = None

    def setUp(self):
        self.finished = False
        self.failure = None
        self.label = None

    def fail_test(self, failure):
        self.failure = failure
        self.finished = True

    def pass_test(self):
        self.finished = True

    def _render_question(self):
        fnt = font.load('Courier')
        self.label = font.Text(fnt, text=self.question, x=10, y=self.window_size[1]-20)

    def _draw(self):
        gl.glClearColor(0.5, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glLoadIdentity()
        self.label.draw()
        self.window.flip()

    def _test_main(self):
        assert self.question

        width, height = self.window_size
        self.window = w = Window(width, height, visible=False, resizable=False)
        w.push_handlers(self)
        self._render_question()
        w.set_visible()

        while not self.finished and not w.has_exit:
            self._draw()
            w.dispatch_events()

        w.close()

        # TODO: Allow entering reason of failure if user aborts
        self.assertTrue(self.finished, msg="Test aborted")
        self.assertIsNone(self.failure, msg=self.failure)


@requires_user_action
class KeyPressWindowEventTestCase(WindowEventsTestCase):
    number_of_checks = 10
    keys = (key.A, key.B, key.C, key.D, key.E, key.F, key.G, key.H, key.I, key.J, key.K, key.L,
            key.M, key.N, key.O, key.P, key.Q, key.R, key.S, key.T, key.U, key.V, key.W, key.X,
            key.Y, key.Z)
    mod_shift_keys = (key.LSHIFT, key.RSHIFT)
    mod_ctrl_keys = (key.LCTRL, key.RCTRL)
    mod_alt_keys = (key.LALT, key.RALT)
    mod_meta_keys = (key.LMETA, key.RMETA)
    mod_meta = key.MOD_SHIFT | key.MOD_ALT

    def setUp(self):
        super(KeyPressWindowEventTestCase, self).setUp()
        self.chosen_symbol = None
        self.chosen_modifiers = None
        self.completely_pressed = False
        self.active_keys = []
        self.checks_passed = 0

    def on_key_press(self, symbol, modifiers):
        print('Press', key.symbol_string(symbol))
        self.active_keys.append(symbol)

        if self.completely_pressed:
            self.fail_test('Key already pressed, no release received.')

        elif self._is_correct_modifier_key(symbol):
            # Does not seem to be correct for modifier keys
            #self._check_modifiers_against_pressed_keys(modifiers)
            pass

        elif self._is_correct_key(symbol):
            self._check_modifiers_against_pressed_keys(modifiers)
            self.completely_pressed = True

    def on_key_release(self, symbol, modifiers):
        print('Release', key.symbol_string(symbol))
        symbol = self._handle_meta_release(symbol)
        if symbol not in self.active_keys:
            self.fail_test('Released key "{}" was not pressed before.'.format(key.symbol_string(symbol)))
        else:
            self.active_keys.remove(symbol)

        if len(self.active_keys) == 0 and self.completely_pressed:
            self.completely_pressed = False
            self.checks_passed += 1
            if self.checks_passed == self.number_of_checks:
                self.pass_test()
            else:
                self._select_next_key()

    def _select_next_key(self):
        self.chosen_symbol = random.choice(self.keys)

        # Little trick, Ctrl, Alt and Shift are lowest modifier values, so everything between 0 and
        # the full combination is a permutation of these three.
        max_modifiers = key.MOD_SHIFT | key.MOD_ALT | key.MOD_CTRL
        # Give a little more weight to key without modifiers
        self.chosen_modifiers = max(0, random.randint(-2, max_modifiers))

        self._update_question()

    def _update_question(self):
        modifiers = []
        if self.chosen_modifiers & key.MOD_SHIFT:
            modifiers.append('<Shift>')
        if self.chosen_modifiers & key.MOD_ALT:
            modifiers.append('<Alt>')
        if self.chosen_modifiers & key.MOD_CTRL:
            modifiers.append('<Ctrl>')

        self.question = """Please press and release:

{} {}


Press Esc if test does not pass.""".format(' '.join(modifiers), key.symbol_string(self.chosen_symbol))
        self._render_question()

    def _is_correct_modifier_key(self, symbol):
        modifier = self._get_modifier_for_key(symbol)
        if modifier == 0:
            return False

        if not self.chosen_modifiers & modifier:
            self.fail_test('Unexpected modifier key "{}"'.format(key.symbol_string(symbol)))

        return True

    def _get_modifier_for_key(self, symbol):
        if symbol in self.mod_shift_keys:
            return key.MOD_SHIFT
        elif symbol in self.mod_alt_keys:
            return key.MOD_ALT
        elif symbol in self.mod_ctrl_keys:
            return key.MOD_CTRL
        elif symbol in self.mod_meta_keys:
            return self.mod_meta
        else:
            return 0

    def _get_modifiers_from_pressed_keys(self):
        modifiers = 0
        for symbol in self.active_keys:
            modifiers |= self._get_modifier_for_key(symbol)
        return modifiers

    def _check_modifiers_against_pressed_keys(self, modifiers):
        modifiers_from_keys = self._get_modifiers_from_pressed_keys()
        if modifiers != modifiers_from_keys:
            self.fail_test('Received modifiers "{}" do not match pressed keys "{}"'.format(
                                key.modifiers_string(modifiers),
                                key.modifiers_string(modifiers_from_keys)))

    def _is_correct_key(self, symbol):
        if not self.chosen_symbol:
            self.fail_test('No more key presses/releases expected.')
            return False

        if self.chosen_symbol != symbol:
            self.fail_test('Received key "{}", but expected "{}"'.format(key.symbol_string(symbol),
                                                                         key.symbol_string(self.chosen_symbol)))
            return False

        return True

    def _handle_meta_release(self, symbol):
        """The meta key can be either released as meta or as alt shift or vv"""
        if symbol in (key.LMETA, key.LALT, key.RMETA, key.RALT):
            if symbol not in self.active_keys:
                if symbol == key.LMETA and key.LALT in self.active_keys:
                    return key.LALT
                if symbol == key.RMETA and key.RALT in self.active_keys:
                    return key.RALT
                if symbol == key.LALT and key.LMETA in self.active_keys:
                    return key.LMETA
                if symbol == key.RALT and key.RMETA in self.active_keys:
                    return key.RMETA
        return symbol

    def test_key_press_release(self):
        """Show several keys to press. Check that the event is triggered for the correct key."""
        self._select_next_key()
        self._test_main()

@requires_user_action
class TextWindowEventsTest(WindowEventsTestCase):
    number_of_checks = 10
    text = '`1234567890-=~!@#$%^&*()_+qwertyuiop[]\\QWERTYUIOP{}|asdfghjkl;\'ASDFGHJKL:"zxcvbnm,./ZXCVBNM<>?'

    def setUp(self):
        super(TextWindowEventsTest, self).setUp()
        self.chosen_text = None
        self.checks_passed = 0

    def on_text(self, text):
        print('on_text', text)
        if text != self.chosen_text:
            self.fail_test('Expected "{}", received "{}"'.format(self.chosen_text, text))
        else:
            self.checks_passed += 1
            if self.checks_passed >= self.number_of_checks:
                self.pass_test()
            else:
                self._select_next_text()

    def _select_next_text(self):
        self.chosen_text = random.choice(self.text)
        self._update_question()

    def _update_question(self):
        self.question = """Please type:

{}


Press Esc if test does not pass.""".format(self.chosen_text)
        self._render_question()

    def test_key_text(self):
        """Show several keys to press. Check that the text events are triggered correctly."""
        self._select_next_text()
        self._test_main()

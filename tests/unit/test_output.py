"""Unit tests para voiceasistent.output."""
import unittest

from voiceasistent.output import OutputWriter


class FakeClipboard:
    def __init__(self, fail_copy=False):
        self.fail_copy = fail_copy
        self.copied = []
        self.text = ""

    def copy(self, text):
        if self.fail_copy:
            raise RuntimeError("clipboard unavailable")
        self.copied.append(text)
        self.text = text

    def paste(self):
        return self.text


class FakeKeyboard:
    def __init__(self):
        self.paste_calls = 0
        self.typed = []
        self.unsupported = set()

    def hotkey_paste(self):
        self.paste_calls += 1

    def type_text(self, text):
        for char in text:
            if char in self.unsupported:
                raise ValueError(f"unsupported char: {char}")
        self.typed.append(text)


class OutputWriterTests(unittest.TestCase):
    def test_paste_happy_path(self):
        clipboard = FakeClipboard()
        keyboard = FakeKeyboard()
        writer = OutputWriter(clipboard, keyboard, mode="paste")
        result = writer.deliver("hola mundo")
        self.assertEqual(result.status, "pasted")
        self.assertEqual(clipboard.text, "hola mundo")
        self.assertEqual(keyboard.paste_calls, 1)
        self.assertEqual(keyboard.typed, [])

    def test_keep_clipboard_preserves_transcription(self):
        clipboard = FakeClipboard()
        writer = OutputWriter(clipboard, FakeKeyboard(), mode="paste", keep_clipboard=True)
        writer.deliver("texto final")
        self.assertEqual(clipboard.text, "texto final")

    def test_empty_text_skipped(self):
        clipboard = FakeClipboard()
        keyboard = FakeKeyboard()
        writer = OutputWriter(clipboard, keyboard, mode="paste")
        result = writer.deliver("   ")
        self.assertEqual(result.status, "skipped")
        self.assertEqual(keyboard.paste_calls, 0)

    def test_clipboard_failure_falls_back_to_typing(self):
        clipboard = FakeClipboard(fail_copy=True)
        keyboard = FakeKeyboard()
        writer = OutputWriter(clipboard, keyboard, mode="paste")
        result = writer.deliver("hola")
        self.assertEqual(result.status, "typed")
        self.assertEqual(keyboard.typed, ["hola"])

    def test_typing_mode_never_pastes(self):
        clipboard = FakeClipboard()
        keyboard = FakeKeyboard()
        writer = OutputWriter(clipboard, keyboard, mode="type")
        result = writer.deliver("hola")
        self.assertEqual(result.status, "typed")
        self.assertEqual(keyboard.paste_calls, 0)

    def test_clipboard_mode_copies_without_pasting(self):
        clipboard = FakeClipboard()
        keyboard = FakeKeyboard()
        writer = OutputWriter(clipboard, keyboard, mode="clipboard")
        result = writer.deliver("hola")
        self.assertEqual(result.status, "copied")
        self.assertEqual(keyboard.paste_calls, 0)
        self.assertEqual(clipboard.text, "hola")


if __name__ == "__main__":
    unittest.main()

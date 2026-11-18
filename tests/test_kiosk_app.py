# -*- coding: utf-8 -*-
"""業務用キオスク端末アプリ サンプルのテスト（標準ライブラリのみ）

実行: python3 -m unittest -v
画面のテストは、ディスプレイがない環境（CIなど）では自動でスキップされます。
"""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kiosk_app as ka  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TestPinGuard(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.guard = ka.PinGuard("1234", max_attempts=3, lockout_sec=30, clock=self.clock)

    def test_correct_pin(self):
        self.assertTrue(self.guard.check("1234"))

    def test_wrong_pin_and_none(self):
        self.assertFalse(self.guard.check("0000"))
        self.assertFalse(self.guard.check(None))
        self.assertFalse(self.guard.check(""))

    def test_lock_after_max_failures(self):
        for _ in range(3):
            self.guard.check("0000")
        self.assertTrue(self.guard.is_locked())
        self.assertEqual(self.guard.remaining_lock_sec(), 30)
        self.assertFalse(self.guard.check("1234"))  # ロック中は正しいPINでも不可

    def test_unlock_after_lockout(self):
        for _ in range(3):
            self.guard.check("0000")
        self.clock.now += 30
        self.assertFalse(self.guard.is_locked())
        self.assertTrue(self.guard.check("1234"))

    def test_success_resets_failures(self):
        self.guard.check("0000")
        self.guard.check("0000")
        self.assertTrue(self.guard.check("1234"))
        self.guard.check("0000")
        self.guard.check("0000")
        self.assertFalse(self.guard.is_locked())


def _make_root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


class TestKioskScreen(unittest.TestCase):
    def setUp(self):
        self.root = _make_root()
        if self.root is None:
            self.skipTest("ディスプレイがないため画面テストをスキップ")
        self.clock = FakeClock()
        self.guard = ka.PinGuard("1234", max_attempts=3, lockout_sec=30, clock=self.clock)
        for target in ("showerror", "showwarning"):
            p = mock.patch.object(ka.messagebox, target)
            p.start()
            self.addCleanup(p.stop)
        self.app = ka.KioskApp(self.root, pin_guard=self.guard)
        self.root.update()

    def tearDown(self):
        if self.root is not None and self._alive():
            self.root.destroy()

    def _alive(self):
        try:
            return bool(self.root.winfo_exists())
        except tk.TclError:
            return False

    def _enter_pin(self, value):
        with mock.patch.object(ka.simpledialog, "askstring", return_value=value):
            self.app.try_exit()

    def _close_window(self, value):
        # Alt+F4 / × と同じ「ウィンドウを閉じる」操作
        with mock.patch.object(ka.simpledialog, "askstring", return_value=value):
            self.root.tk.call(self.root.protocol("WM_DELETE_WINDOW"))

    def test_starts_fullscreen_on_home(self):
        self.assertTrue(self.root.attributes("-fullscreen"))
        self.assertEqual(self.app.current_page, ka.HOME_PAGE)

    def test_navigation_only_allowed_pages(self):
        self.app.show_page("お知らせ")
        self.assertEqual(self.app.current_page, "お知らせ")
        self.app.show_page("設定画面")  # 許可リストにない
        self.assertEqual(self.app.current_page, "お知らせ")

    def test_idle_returns_home(self):
        with mock.patch.object(ka, "IDLE_TIMEOUT_SEC", 0.2):
            self.app.show_page("店舗情報")
            self.root.after(500, self.root.quit)
            self.root.mainloop()
        self.assertEqual(self.app.current_page, ka.HOME_PAGE)

    def test_wrong_pin_or_cancel_keeps_running(self):
        self._enter_pin("0000")
        self._enter_pin(None)
        self.assertTrue(self._alive())
        ka.messagebox.showerror.assert_called_once()

    def test_close_window_requires_pin(self):
        self._close_window("0000")
        self.assertTrue(self._alive())
        self._close_window("1234")
        self.assertFalse(self._alive())

    def test_lockout_blocks_exit(self):
        for _ in range(3):
            self._enter_pin("0000")
        self._enter_pin("1234")  # ロック中
        self.assertTrue(self._alive())
        self.clock.now += 30
        self._enter_pin("1234")
        self.assertFalse(self._alive())

    def test_correct_pin_exits(self):
        self._enter_pin("1234")
        self.assertFalse(self._alive())


if __name__ == "__main__":
    unittest.main()

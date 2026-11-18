#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""業務用キオスク端末アプリ サンプル

全画面で起動し、許可されたページだけを表示するキオスク型アプリ。
- 表示できるページは ALLOWED_PAGES で定義したものだけ
- 一定時間操作がないとホーム画面へ自動で戻る
- 終了は管理者PINを入力したときだけ可能（ウィンドウを閉じる操作も含む）
- PINを続けて間違えると、一定時間ロックする

実案件（業務用Android端末向け・Python製）の簡易再現として、
PC上で動くデモ版を Tkinter で実装したサンプル。

※ アプリ側で防げるのはアプリ内の操作まで。Alt+Tab や OS のショートカットなど
  OS 側の操作は、実機では OS のキオスクモード（Android の画面固定 / 専用端末モード、
  Windows の割り当てられたアクセス 等）と組み合わせて制限する。
"""

import hmac
import os
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

# ===== 設定 =====
EXIT_PIN = os.environ.get("KIOSK_EXIT_PIN", "1234")  # 管理者PIN（環境変数で上書き可能）
MAX_PIN_ATTEMPTS = 3       # 続けて間違えられる回数
LOCKOUT_SEC = 30           # 上限に達したときのロック時間（秒）
IDLE_TIMEOUT_SEC = 60      # 無操作でホームへ戻るまでの秒数
APP_TITLE = "業務用端末（サンプル）"
HOME_PAGE = "ホーム"

# 表示を許可するページ（タイトルと本文）
ALLOWED_PAGES = {
    "ホーム": "こちらは業務用端末のホーム画面です。\n上のボタンから案内ページを開けます。",
    "お知らせ": "【お知らせ】\n・本日の営業時間は 9:00〜21:00 です。\n・体調がすぐれない場合はスタッフへお声がけください。",
    "利用案内": "【利用案内】\n1. ご用件のボタンを押してください。\n2. 分からない場合はスタッフへお声がけください。",
    "店舗情報": "【店舗情報】\n営業時間：9:00〜21:00\n所在地：サンプル県サンプル市 1-2-3",
}


class PinGuard:
    """管理者PINの照合と、連続失敗時のロックを管理する（画面に依存しない）"""

    def __init__(self, pin, max_attempts=MAX_PIN_ATTEMPTS, lockout_sec=LOCKOUT_SEC, clock=time.monotonic):
        self._pin = pin
        self._max_attempts = max_attempts
        self._lockout_sec = lockout_sec
        self._clock = clock
        self._failures = 0
        self._locked_until = 0.0

    def remaining_lock_sec(self):
        return max(0, int(self._locked_until - self._clock() + 0.999))

    def is_locked(self):
        return self.remaining_lock_sec() > 0

    def check(self, entered):
        # 正しければ True。ロック中は入力内容にかかわらず False
        if self.is_locked():
            return False
        if entered is not None and hmac.compare_digest(entered.encode("utf-8"), self._pin.encode("utf-8")):
            self._failures = 0
            return True
        self._failures += 1
        if self._failures >= self._max_attempts:
            self._failures = 0
            self._locked_until = self._clock() + self._lockout_sec
        return False


class KioskApp:
    def __init__(self, root, pin_guard=None):
        self.root = root
        self.pin_guard = pin_guard or PinGuard(EXIT_PIN)
        self.current_page = None
        self._idle_job = None

        self.root.title(APP_TITLE)
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1f2937")
        # ウィンドウを閉じる操作（Alt+F4 / ×）でも管理者PINを必須にする
        self.root.protocol("WM_DELETE_WINDOW", self.try_exit)

        # ページ切り替えボタン
        nav = tk.Frame(root, bg="#111827")
        nav.pack(side="top", fill="x")
        for name in ALLOWED_PAGES:
            btn = tk.Button(
                nav, text=name, font=("sans-serif", 16),
                command=lambda n=name: self.show_page(n),
            )
            btn.pack(side="left", padx=6, pady=8)

        # 管理者用終了ボタン（小さく右端に配置）
        exit_btn = tk.Button(
            nav, text="管理", font=("sans-serif", 10),
            command=self.try_exit,
        )
        exit_btn.pack(side="right", padx=6, pady=8)

        # 本文エリア
        self.body = tk.Label(
            root, text="", font=("sans-serif", 20),
            bg="#1f2937", fg="#f9fafb", justify="left", anchor="nw",
        )
        self.body.pack(side="top", fill="both", expand=True, padx=32, pady=32)

        # 操作を検知してアイドルタイマーをリセット
        root.bind_all("<Any-ButtonPress>", self._on_activity)
        root.bind_all("<Any-KeyPress>", self._on_activity)

        self.show_page(HOME_PAGE)

    def show_page(self, name):
        # 許可リストにないページは表示しない
        if name not in ALLOWED_PAGES:
            return
        self.current_page = name
        self.body.config(text=ALLOWED_PAGES[name])
        self._reset_idle_timer()

    def _on_activity(self, _event=None):
        self._reset_idle_timer()

    def _reset_idle_timer(self):
        if self._idle_job is not None:
            self.root.after_cancel(self._idle_job)
        self._idle_job = self.root.after(int(IDLE_TIMEOUT_SEC * 1000), self._go_home)

    def _go_home(self):
        self._idle_job = None
        self.current_page = HOME_PAGE
        self.body.config(text=ALLOWED_PAGES[HOME_PAGE])

    def try_exit(self):
        if self.pin_guard.is_locked():
            messagebox.showwarning(
                "管理者確認",
                f"PINの入力に続けて失敗したため、ロック中です。\n{self.pin_guard.remaining_lock_sec()}秒後に再度お試しください。",
                parent=self.root,
            )
            return
        pin = simpledialog.askstring(
            "管理者確認", "終了するには管理者PINを入力してください",
            show="*", parent=self.root,
        )
        if pin is None:  # キャンセル
            return
        if self.pin_guard.check(pin):
            self.root.destroy()
        elif self.pin_guard.is_locked():
            messagebox.showwarning(
                "管理者確認",
                f"PINの入力に続けて失敗したため、{self.pin_guard.remaining_lock_sec()}秒間ロックします。",
                parent=self.root,
            )
        else:
            messagebox.showerror("管理者確認", "PINが違います。", parent=self.root)


def main():
    root = tk.Tk()
    KioskApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

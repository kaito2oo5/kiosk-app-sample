#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""業務用キオスク端末アプリ サンプル

全画面で起動し、許可されたページだけを表示するキオスク型アプリ。
- 表示できるページは ALLOWED_PAGES で定義したものだけ
- 一定時間操作がないとホーム画面へ自動で戻る
- 終了は管理者PINを入力したときだけ可能

実案件（業務用Android端末向け・Python製）の簡易再現として、
PC上で動くデモ版を Tkinter で実装したサンプル。
"""

import tkinter as tk
from tkinter import simpledialog

# ===== 設定 =====
EXIT_PIN = "1234"          # 管理者PIN（終了時に必要）
IDLE_TIMEOUT_SEC = 60      # 無操作でホームへ戻るまでの秒数
APP_TITLE = "業務用端末（サンプル）"

# 表示を許可するページ（タイトルと本文）
ALLOWED_PAGES = {
    "ホーム": "こちらは業務用端末のホーム画面です。\n上のボタンから案内ページを開けます。",
    "お知らせ": "【お知らせ】\n・本日の営業時間は 9:00〜21:00 です。\n・体調がすぐれない場合はスタッフへお声がけください。",
    "利用案内": "【利用案内】\n1. ご用件のボタンを押してください。\n2. 分からない場合はスタッフへお声がけください。",
    "店舗情報": "【店舗情報】\n営業時間：9:00〜21:00\n所在地：サンプル県サンプル市 1-2-3",
}


class KioskApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#1f2937")
        # ウィンドウを閉じる操作（Alt+F4 / ×）でも管理者PINを必須にする
        self.root.protocol("WM_DELETE_WINDOW", self.try_exit)
        self._idle_job = None

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

        self.show_page("ホーム")
        self._reset_idle_timer()

    def show_page(self, name):
        self.body.config(text=ALLOWED_PAGES[name])
        self._reset_idle_timer()

    def _on_activity(self, _event=None):
        self._reset_idle_timer()

    def _reset_idle_timer(self):
        if self._idle_job is not None:
            self.root.after_cancel(self._idle_job)
        self._idle_job = self.root.after(IDLE_TIMEOUT_SEC * 1000, self._go_home)

    def _go_home(self):
        self.body.config(text=ALLOWED_PAGES["ホーム"])

    def try_exit(self):
        pin = simpledialog.askstring(
            "管理者確認", "終了するには管理者PINを入力してください",
            show="*", parent=self.root,
        )
        if pin == EXIT_PIN:
            self.root.destroy()


def main():
    root = tk.Tk()
    KioskApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

import flet as ft
from ymobile_fetcher import YmobileFetcher

def main(page: ft.Page):
    page.title = "Y!mobile Checker"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    # スマホ向けにウィンドウサイズ設定（PCプレビュー用）
    page.window_width = 360
    page.window_height = 640

    # --- UIパーツの定義 ---
    
    # 1. ログイン画面用パーツ
    id_input = ft.TextField(label="Y!mobile ID (電話番号)", width=280)
    pass_input = ft.TextField(label="パスワード", password=True, can_reveal_password=True, width=280)
    login_error_text = ft.Text("", color=ft.colors.RED)
    
    # 2. メイン画面用パーツ
    status_text = ft.Text("準備中...", size=16)
    center_text = ft.Text("", size=30, weight=ft.FontWeight.BOLD)
    chart = ft.PieChart(sections=[], sections_space=0, center_space_radius=70, height=200)

    # --- ロジック ---

    def save_and_login(e):
        """ログインボタンが押された時の処理"""
        if not id_input.value or not pass_input.value:
            login_error_text.value = "IDとパスワードを入力してください"
            page.update()
            return
            
        # 情報を保存 (スマホ内に保存される)
        page.client_storage.set("ym_id", id_input.value)
        page.client_storage.set("ym_pass", pass_input.value)
        
        # 画面切り替え
        show_dashboard()

    def logout(e):
        """ログアウト処理"""
        page.client_storage.clear()
        id_input.value = ""
        pass_input.value = ""
        login_error_text.value = ""
        show_login_screen()

    def fetch_data_action(e=None):
        """データの更新処理"""
        status_text.value = "通信中..."
        # グラフをグレーにしてロード中感を出す
        chart.sections = [ft.PieChartSection(value=100, color=ft.colors.GREY_300, radius=20)]
        center_text.value = "..."
        page.update()

        # 保存されたID/PASSを取得
        saved_id = page.client_storage.get("ym_id")
        saved_pass = page.client_storage.get("ym_pass")
        
        # フェッチャーの初期化
        fetcher = YmobileFetcher(saved_id, saved_pass)
        
        # データ取得 (force_refresh=Trueで毎回最新を取りに行く)
        data = fetcher.get_data(force_refresh=True)

        if data:
            rem = data['remaining_gb']
            used = data['used_gb']
            
            chart.sections = [
                ft.PieChartSection(value=used, title="", color=ft.colors.RED_400, radius=20),
                ft.PieChartSection(value=rem, title="", color=ft.colors.BLUE_400, radius=30),
            ]
            center_text.value = f"{rem}\nGB"
            status_text.value = f"更新: {data['last_updated']}"
        else:
            status_text.value = "取得失敗 (ID/PASSを確認してください)"
            center_text.value = "?"
            # 認証失敗の可能性があるので、ログアウトボタンを目立たせてもいいかも
        
        page.update()

    # --- 画面描画関数 ---

    def show_login_screen():
        """ログイン画面を表示"""
        page.clean()
        page.add(
            ft.Column([
                ft.Icon(ft.icons.LOCK_OPEN, size=50, color=ft.colors.RED),
                ft.Text("Y!mobile ログイン", size=24, weight="bold"),
                ft.Container(height=20),
                id_input,
                pass_input,
                ft.Container(height=10),
                login_error_text,
                ft.Container(height=10),
                ft.ElevatedButton("ログインして保存", on_click=save_and_login, width=200, height=50),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def show_dashboard():
        """メイン画面を表示"""
        page.clean()
        page.add(
            ft.Column([
                ft.Text("データ残量", size=24, weight="bold"),
                ft.Container(height=20),
                ft.Stack([
                    chart,
                    ft.Container(content=center_text, alignment=ft.alignment.center, width=200, height=200),
                ], width=200, height=200),
                ft.Container(height=20),
                status_text,
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton("更新", icon=ft.icons.REFRESH, on_click=fetch_data_action),
                    ft.OutlinedButton("ログアウト", icon=ft.icons.LOGOUT, on_click=logout)
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        # 画面表示後にデータを読みに行く
        fetch_data_action()

    # --- アプリ起動時の分岐 ---
    
    # 保存されたIDがあるかチェック
    if page.client_storage.contains_key("ym_id"):
        show_dashboard()
    else:
        show_login_screen()

ft.app(target=main)
import flet as ft
import sys
import traceback

# エラーハンドリング用のラッパー
def safe_import():
    try:
        from ymobile_fetcher import YmobileFetcher
        return YmobileFetcher
    except Exception as e:
        print(f"Import Error: {e}")
        traceback.print_exc()
        return None

YmobileFetcher = safe_import()

def main(page: ft.Page):
    try:
        page.title = "Y!mobile Checker"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        # スマホ向けにウィンドウサイズ設定（PCプレビュー用）
        page.window_width = 360
        page.window_height = 640

        # デバッグ用: エラー表示用テキスト
        debug_text = ft.Text("", color=ft.colors.RED, size=12)

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
            try:
                if not id_input.value or not pass_input.value:
                    login_error_text.value = "IDとパスワードを入力してください"
                    page.update()
                    return
                    
                # 情報を保存 (スマホ内に保存される)
                page.client_storage.set("ym_id", id_input.value)
                page.client_storage.set("ym_pass", pass_input.value)
                
                # 画面切り替え
                show_dashboard()
            except Exception as ex:
                login_error_text.value = f"エラー: {str(ex)}"
                page.update()

        def logout(e):
            """ログアウト処理"""
            try:
                page.client_storage.clear()
                id_input.value = ""
                pass_input.value = ""
                login_error_text.value = ""
                show_login_screen()
            except Exception as ex:
                print(f"Logout error: {ex}")

        def fetch_data_action(e=None):
            """データの更新処理"""
            try:
                if YmobileFetcher is None:
                    status_text.value = "モジュール読み込みエラー"
                    page.update()
                    return

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
                
                page.update()
            except Exception as ex:
                status_text.value = f"エラー: {str(ex)}"
                center_text.value = "?"
                page.update()
                traceback.print_exc()

        # --- 画面描画関数 ---

        def show_login_screen():
            """ログイン画面を表示"""
            try:
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
                        debug_text,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            except Exception as ex:
                print(f"Show login screen error: {ex}")
                traceback.print_exc()

        def show_dashboard():
            """メイン画面を表示"""
            try:
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
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        debug_text,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
                # 画面表示後にデータを読みに行く
                fetch_data_action()
            except Exception as ex:
                print(f"Show dashboard error: {ex}")
                traceback.print_exc()

        # --- アプリ起動時の分岐 ---
        
        # 保存されたIDがあるかチェック
        if page.client_storage.contains_key("ym_id"):
            show_dashboard()
        else:
            show_login_screen()
            
    except Exception as e:
        print(f"Main Error: {e}")
        traceback.print_exc()
        # 最低限のエラー画面を表示
        try:
            page.add(
                ft.Column([
                    ft.Text("アプリ起動エラー", size=20, color=ft.colors.RED),
                    ft.Text(str(e), size=12),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        except:
            pass

if __name__ == "__main__":
    ft.app(target=main)
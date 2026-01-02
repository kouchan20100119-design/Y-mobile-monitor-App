import flet as ft
import sys
import traceback
import os

# デバッグログ用のファイル
DEBUG_LOG = []

def log_debug(msg):
    """デバッグメッセージをログに記録"""
    DEBUG_LOG.append(msg)
    print(msg)

log_debug("=== App starting ===")

# モジュールのインポート試行
YmobileFetcher = None
try:
    log_debug("Attempting to import ymobile_fetcher...")
    from ymobile_fetcher import YmobileFetcher
    log_debug("Import successful!")
except Exception as e:
    log_debug(f"Import FAILED: {e}")
    log_debug(f"Traceback: {traceback.format_exc()}")

def main(page: ft.Page):
    log_debug("Main function started")
    
    try:
        page.title = "Y!mobile Checker"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.padding = 20
        
        log_debug("Page configured")

        # デバッグ情報表示用
        debug_info = ft.Column([], scroll=ft.ScrollMode.AUTO, height=200)
        
        def update_debug_info():
            """デバッグ情報を更新"""
            debug_info.controls.clear()
            for msg in DEBUG_LOG[-10:]:  # 最新10件
                debug_info.controls.add(ft.Text(msg, size=10, color=ft.colors.GREY))
            page.update()

        # --- UIパーツの定義 ---
        
        # 1. ログイン画面用パーツ
        id_input = ft.TextField(
            label="Y!mobile ID (電話番号)", 
            width=280,
            keyboard_type=ft.KeyboardType.PHONE
        )
        pass_input = ft.TextField(
            label="パスワード", 
            password=True, 
            can_reveal_password=True, 
            width=280
        )
        login_error_text = ft.Text("", color=ft.colors.RED)
        
        # 2. メイン画面用パーツ
        status_text = ft.Text("準備中...", size=16)
        center_text = ft.Text("", size=30, weight=ft.FontWeight.BOLD)
        chart = ft.PieChart(
            sections=[], 
            sections_space=0, 
            center_space_radius=70, 
            height=200,
            width=200
        )

        log_debug("UI components created")

        # --- ロジック ---

        def save_and_login(e):
            """ログインボタンが押された時の処理"""
            log_debug("Login button clicked")
            try:
                if not id_input.value or not pass_input.value:
                    login_error_text.value = "IDとパスワードを入力してください"
                    log_debug("Login validation failed")
                    page.update()
                    return
                
                log_debug(f"Saving credentials for ID: {id_input.value[:3]}***")
                
                # 情報を保存
                page.client_storage.set("ym_id", id_input.value)
                page.client_storage.set("ym_pass", pass_input.value)
                
                log_debug("Credentials saved, showing dashboard")
                show_dashboard()
            except Exception as ex:
                error_msg = f"Login error: {str(ex)}"
                log_debug(error_msg)
                login_error_text.value = error_msg
                update_debug_info()
                page.update()

        def logout(e):
            """ログアウト処理"""
            log_debug("Logout clicked")
            try:
                page.client_storage.clear()
                id_input.value = ""
                pass_input.value = ""
                login_error_text.value = ""
                show_login_screen()
            except Exception as ex:
                log_debug(f"Logout error: {ex}")

        def fetch_data_action(e=None):
            """データの更新処理"""
            log_debug("Fetch data action started")
            try:
                if YmobileFetcher is None:
                    error_msg = "エラー: ymobile_fetcherモジュールが読み込めません"
                    log_debug(error_msg)
                    status_text.value = error_msg
                    update_debug_info()
                    page.update()
                    return

                status_text.value = "通信中..."
                chart.sections = [ft.PieChartSection(
                    value=100, 
                    color=ft.colors.GREY_300, 
                    radius=20
                )]
                center_text.value = "..."
                page.update()

                # 保存されたID/PASSを取得
                saved_id = page.client_storage.get("ym_id")
                saved_pass = page.client_storage.get("ym_pass")
                
                log_debug(f"Fetching data for ID: {saved_id[:3] if saved_id else 'None'}***")
                
                # フェッチャーの初期化
                fetcher = YmobileFetcher(saved_id, saved_pass)
                
                log_debug("Fetcher initialized, getting data...")
                # データ取得
                data = fetcher.get_data(force_refresh=True)

                if data:
                    log_debug(f"Data received: {data['remaining_gb']}GB remaining")
                    rem = data['remaining_gb']
                    used = data['used_gb']
                    
                    chart.sections = [
                        ft.PieChartSection(
                            value=used, 
                            title="", 
                            color=ft.colors.RED_400, 
                            radius=20
                        ),
                        ft.PieChartSection(
                            value=rem, 
                            title="", 
                            color=ft.colors.BLUE_400, 
                            radius=30
                        ),
                    ]
                    center_text.value = f"{rem}\nGB"
                    status_text.value = f"更新: {data['last_updated']}"
                else:
                    log_debug("Data fetch failed")
                    status_text.value = "取得失敗 (ID/PASSを確認)"
                    center_text.value = "?"
                
                update_debug_info()
                page.update()
                
            except Exception as ex:
                error_msg = f"Fetch error: {str(ex)}"
                log_debug(error_msg)
                log_debug(f"Traceback: {traceback.format_exc()}")
                status_text.value = f"エラー: {str(ex)[:50]}"
                center_text.value = "?"
                update_debug_info()
                page.update()

        # --- 画面描画関数 ---

        def show_login_screen():
            """ログイン画面を表示"""
            log_debug("Showing login screen")
            try:
                page.clean()
                
                # モジュール読み込み状況を表示
                module_status = "✅ モジュール読み込み成功" if YmobileFetcher else "❌ モジュール読み込み失敗"
                
                page.add(
                    ft.Column([
                        ft.Icon(ft.icons.LOCK_OPEN, size=50, color=ft.colors.RED),
                        ft.Text("Y!mobile ログイン", size=24, weight="bold"),
                        ft.Text(module_status, size=12, color=ft.colors.BLUE),
                        ft.Container(height=20),
                        id_input,
                        pass_input,
                        ft.Container(height=10),
                        login_error_text,
                        ft.Container(height=10),
                        ft.ElevatedButton(
                            "ログインして保存", 
                            on_click=save_and_login, 
                            width=200, 
                            height=50
                        ),
                        ft.Container(height=20),
                        ft.ExpansionTile(
                            title=ft.Text("デバッグ情報", size=12),
                            controls=[debug_info],
                            initially_expanded=False
                        ),
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO
                    )
                )
                update_debug_info()
                log_debug("Login screen displayed")
                
            except Exception as ex:
                log_debug(f"Show login error: {ex}")
                log_debug(f"Traceback: {traceback.format_exc()}")

        def show_dashboard():
            """メイン画面を表示"""
            log_debug("Showing dashboard")
            try:
                page.clean()
                page.add(
                    ft.Column([
                        ft.Text("データ残量", size=24, weight="bold"),
                        ft.Container(height=20),
                        ft.Stack([
                            chart,
                            ft.Container(
                                content=center_text, 
                                alignment=ft.alignment.center, 
                                width=200, 
                                height=200
                            ),
                        ], width=200, height=200),
                        ft.Container(height=20),
                        status_text,
                        ft.Container(height=20),
                        ft.Row([
                            ft.ElevatedButton(
                                "更新", 
                                icon=ft.icons.REFRESH, 
                                on_click=fetch_data_action
                            ),
                            ft.OutlinedButton(
                                "ログアウト", 
                                icon=ft.icons.LOGOUT, 
                                on_click=logout
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=20),
                        ft.ExpansionTile(
                            title=ft.Text("デバッグ情報", size=12),
                            controls=[debug_info],
                            initially_expanded=False
                        ),
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO
                    )
                )
                update_debug_info()
                log_debug("Dashboard displayed, fetching data...")
                # 画面表示後にデータを読みに行く
                fetch_data_action()
                
            except Exception as ex:
                log_debug(f"Show dashboard error: {ex}")
                log_debug(f"Traceback: {traceback.format_exc()}")

        # --- アプリ起動時の分岐 ---
        
        log_debug("Checking for saved credentials...")
        # 保存されたIDがあるかチェック
        if page.client_storage.contains_key("ym_id"):
            log_debug("Saved credentials found")
            show_dashboard()
        else:
            log_debug("No saved credentials")
            show_login_screen()
            
    except Exception as e:
        error_msg = f"Main error: {e}"
        log_debug(error_msg)
        log_debug(f"Traceback: {traceback.format_exc()}")
        
        # 最低限のエラー画面を表示
        try:
            page.clean()
            page.add(
                ft.Column([
                    ft.Text("アプリ起動エラー", size=20, color=ft.colors.RED, weight="bold"),
                    ft.Container(height=10),
                    ft.Text(str(e), size=12),
                    ft.Container(height=20),
                    ft.Text("デバッグログ:", size=14, weight="bold"),
                    ft.Column([
                        ft.Text(msg, size=10) for msg in DEBUG_LOG[-20:]
                    ], scroll=ft.ScrollMode.AUTO, height=300),
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO
                )
            )
        except:
            pass

if __name__ == "__main__":
    log_debug("Starting Flet app...")
    ft.app(target=main)
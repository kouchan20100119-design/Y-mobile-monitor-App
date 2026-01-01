"""
Y!mobile データ残量取得（Android向け）
スマホ上でバックグラウンド実行することを想定した軽量版
"""

import json
import sys
import io
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup

# Windowsでの絵文字出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ==================== 設定エリア ====================
# ここに自分の認証情報を入力してください
YMOBILE_ID = "YOUR_ID"  # Y!mobile ID
YMOBILE_PASSWORD = "YOUR_PASSWORD"  # パスワード

# キャッシュ設定（分単位）
CACHE_DURATION_MINUTES = 15  # 15分ごとに更新
# ==================================================


class YmobileFetcher:
    """軽量・高速なデータ取得クラス"""
    
    def __init__(self):
        self.mobile_id = YMOBILE_ID
        self.password = YMOBILE_PASSWORD
        self.cache_file = "ymobile_cache.json"
        self.cache_duration = timedelta(minutes=CACHE_DURATION_MINUTES)
    
    def get_cached_data(self) -> Optional[Dict]:
        """キャッシュからデータを読み込み"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            cached_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cached_time < self.cache_duration:
                remaining_seconds = (self.cache_duration - (datetime.now() - cached_time)).total_seconds()
                print(f"✅ キャッシュ使用（次回更新まで {int(remaining_seconds/60)}分）")
                return cache
            
            print("⏰ キャッシュ期限切れ - 新規取得します")
            return None
            
        except FileNotFoundError:
            print("📝 初回実行 - データを取得します")
            return None
        except Exception as e:
            print(f"⚠️ キャッシュ読み込みエラー: {e}")
            return None
    
    def save_cache(self, data: Dict):
        """キャッシュに保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ キャッシュ保存エラー: {e}")
    
    def _login(self) -> requests.Session:
        """ログイン処理"""
        session = requests.Session()
        
        # ログインページを取得してticketを取得
        r = session.get('https://my.ymobile.jp/muc/d/webLink/doSend/MWBWL0130')
        soup = BeautifulSoup(r.text, 'html.parser')
        ticket_input = soup.find('input', type='hidden')
        
        if not ticket_input:
            raise Exception("ログインページのticketが見つかりません")
        
        ticket = ticket_input.get('value')
        
        # ログイン
        payload = {
            'telnum': self.mobile_id,
            'password': self.password,
            'ticket': ticket
        }
        session.post('https://id.my.ymobile.jp/sbid_auth/type1/2.0/login.php', data=payload)
        
        return session
    
    def fetch_fresh_data(self) -> Optional[Dict]:
        """新規データ取得"""
        try:
            print("🔐 ログイン中...")
            session = self._login()
            
            # データ取得ページへ
            print("📊 データ取得中...")
            r = session.get('https://my.ymobile.jp/muc/d/webLink/doSend/MRERE0000')
            soup = BeautifulSoup(r.text, 'html.parser')
            auth_tokens = soup.find_all('input', type='hidden')
            
            if len(auth_tokens) < 2:
                raise Exception("認証トークンの取得に失敗しました")
            
            payload = {
                'mfiv': auth_tokens[0].get('value'),
                'mfym': auth_tokens[1].get('value'),
            }
            
            req = session.post('https://re61.my.ymobile.jp/resfe/top/', data=payload)
            data = BeautifulSoup(req.text, 'html.parser')
            
            # データ解析
            result = self._parse_data(data)
            
            if result:
                print(f"✅ 取得成功: {result['remaining_gb']}GB / {result['total_gb']}GB 残り")
                return result
            else:
                print("❌ データ解析失敗")
                return None
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """HTMLからデータを抽出"""
        try:
            # 参考リポジトリの方法でデータを取得
            ds = soup.find(class_="list-toggle-content js-toggle-content m-top-20")
            if not ds:
                raise Exception("データテーブルが見つかりません")
            
            tables = ds.find_all("table")
            if len(tables) < 4:
                raise Exception(f"テーブルが不足しています（{len(tables)}個）")
            
            # kurikoshi (繰越)
            kurikoshi_text = tables[0].find("tbody").find("td").text.replace("\t", "").replace("\n", "").replace("GB", "").strip()
            kurikoshi = float(kurikoshi_text)
            
            # kihon (基本)
            kihon_text = tables[1].find("tbody").find_all("tr")[1].find("td").text.replace("\t", "").replace("\n", "").replace("GB", "").strip()
            kihon = float(kihon_text)
            
            # yuryou (有料)
            yuryou_text = tables[2].find("tbody").find("tr").find("td").text.replace("\t", "").replace("\n", "").replace("GB", "").strip()
            yuryou = float(yuryou_text)
            
            # used (使用済み)
            used_text = tables[3].find("tbody").find("tr").find("td").text.replace("\t", "").replace("\n", "").replace("GB", "").strip()
            used = float(used_text)
            
            # 残量はtotal-使用済み
            total = kihon + kurikoshi + yuryou
            remaining = total - used
            percentage = (used / total) * 100 if total > 0 else 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "remaining_gb": round(remaining, 2),
                "total_gb": round(total, 2),
                "used_gb": round(used, 2),
                "percentage": round(percentage, 1),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "kurikoshi_gb": round(kurikoshi, 2),
                "kihon_gb": round(kihon, 2),
                "yuryou_gb": round(yuryou, 2)
            }
            
        except Exception as e:
            print(f"⚠️ データ解析エラー: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_data(self, force_refresh: bool = False) -> Optional[Dict]:
        """データ取得のメイン関数"""
        
        # キャッシュチェック
        if not force_refresh:
            cached = self.get_cached_data()
            if cached:
                return cached
        
        # 新規取得
        print("🚀 データ取得開始...")
        data = self.fetch_fresh_data()
        
        if data:
            self.save_cache(data)
        
        return data


def main():
    """スタンドアロン実行用"""
    
    # 認証情報チェック
    if YMOBILE_PASSWORD == ["YOUR_PASSWORD", "your_password_here"]:
        print("=" * 60)
        print("❌ エラー: パスワードが設定されていません")
        print("=" * 60)
        print("\nコードの先頭部分を編集してください:")
        print('YMOBILE_PASSWORD = "your_password_here"')
        print("                      ↓")
        print('YMOBILE_PASSWORD = "あなたの実際のパスワード"')
        print("=" * 60)
        return
    
    print("=" * 60)
    print("📱 Y!mobile データ残量チェッカー")
    print("=" * 60)
    
    fetcher = YmobileFetcher()
    data = fetcher.get_data()
    
    if data:
        print("\n" + "=" * 60)
        print("📊 取得結果")
        print("=" * 60)
        print(f"更新日時: {data['last_updated']}")
        print(f"残量: {data['remaining_gb']} GB")
        print(f"使用量: {data['used_gb']} GB / {data['total_gb']} GB")
        print(f"使用率: {data['percentage']}%")
        print("=" * 60)
        
        # Android用JSON出力
        print("\n📄 JSON出力 (Android アプリ用):")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("\n❌ データ取得失敗")


if __name__ == "__main__":
    main()
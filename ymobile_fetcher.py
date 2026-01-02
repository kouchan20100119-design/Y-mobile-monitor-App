"""
Y!mobile データ残量取得クラス（汎用版）
"""
import json
import sys
import io
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup

# Windowsでの絵文字出力対応
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

CACHE_DURATION_MINUTES = 15

class YmobileFetcher:
    """軽量・高速なデータ取得クラス"""
    
    # ★変更点: 初期化時にIDとパスワードを受け取るように変更
    def __init__(self, mobile_id: str, password: str, cache_dir: str = None):
        self.mobile_id = mobile_id
        self.password = password
        
        # キャッシュファイルの保存場所設定
        if cache_dir:
            self.cache_file = os.path.join(cache_dir, "ymobile_cache.json")
        else:
            self.cache_file = "ymobile_cache.json"
            
        self.cache_duration = timedelta(minutes=CACHE_DURATION_MINUTES)
    
    def get_cached_data(self) -> Optional[Dict]:
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            cached_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cached_time < self.cache_duration:
                return cache
            return None
        except:
            return None
    
    def save_cache(self, data: Dict):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")
    
    def _login(self) -> requests.Session:
        session = requests.Session()
        # ログインページを取得してticketを取得
        r = session.get('https://my.ymobile.jp/muc/d/webLink/doSend/MWBWL0130')
        soup = BeautifulSoup(r.text, 'html.parser')
        ticket_input = soup.find('input', type='hidden')
        
        if not ticket_input:
            raise Exception("ログインページ接続エラー")
        
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
        try:
            session = self._login()
            
            # データ取得ページへ
            r = session.get('https://my.ymobile.jp/muc/d/webLink/doSend/MRERE0000')
            soup = BeautifulSoup(r.text, 'html.parser')
            auth_tokens = soup.find_all('input', type='hidden')
            
            if len(auth_tokens) < 2:
                raise Exception("認証エラー: IDかパスワードが間違っている可能性があります")
            
            payload = {
                'mfiv': auth_tokens[0].get('value'),
                'mfym': auth_tokens[1].get('value'),
            }
            
            req = session.post('https://re61.my.ymobile.jp/resfe/top/', data=payload)
            data = BeautifulSoup(req.text, 'html.parser')
            return self._parse_data(data)
                
        except Exception as e:
            print(f"エラー: {e}")
            return None
    
    def _parse_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        try:
            ds = soup.find(class_="list-toggle-content js-toggle-content m-top-20")
            if not ds: return None
            
            tables = ds.find_all("table")
            if len(tables) < 4: return None
            
            def get_val(table_idx, row_idx=0):
                rows = tables[table_idx].find("tbody").find_all("tr")
                txt = rows[row_idx].find("td").text
                return float(txt.replace("\t", "").replace("\n", "").replace("GB", "").strip())

            kurikoshi = get_val(0)
            kihon = get_val(1, 1) # 基本は2行目にあることが多い
            yuryou = get_val(2)
            used = get_val(3)
            
            total = kihon + kurikoshi + yuryou
            remaining = total - used
            percentage = (used / total) * 100 if total > 0 else 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "remaining_gb": round(remaining, 2),
                "total_gb": round(total, 2),
                "used_gb": round(used, 2),
                "percentage": round(percentage, 1),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        except:
            return None
    
    def get_data(self, force_refresh: bool = False) -> Optional[Dict]:
        if not force_refresh:
            cached = self.get_cached_data()
            if cached: return cached
        
        data = self.fetch_fresh_data()
        if data: self.save_cache(data)
        return data
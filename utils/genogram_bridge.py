import requests
import json
import urllib.parse
# pip install lzstring
from lzstring import LZString

GENOGRAM_API_URL = "http://localhost:3000/api/generate"
GENOGRAM_EDITOR_URL = "http://localhost:3000"

def generate_genogram_url(text: str = "", files: list = None, api_key: str = ""):
    """
    Genogram Editor APIを呼び出し、結果を埋め込んだURLを生成する関数
    
    Args:
        text (str): 家族構成の説明テキスト
        files (list): アップロードされたファイルのリスト (StreamlitのUploadedFileなど)
        api_key (str): Gemini API Key (省略可)
        
    Returns:
        str: ジェノグラムエディタを開くためのURL (エラー時はNone)
    """
    try:
        # 1. APIへのPOSTリクエスト作成
        files_data = []
        if files:
            for f in files:
                # StreamlitのUploadedFileはgetvalue()でbytesを取得
                file_bytes = f.getvalue()
                files_data.append(('files', (f.name, file_bytes, f.type)))
        
        data = {
            'text': text,
            'apiKey': api_key
        }
        
        # 2. API送信
        response = requests.post(GENOGRAM_API_URL, data=data, files=files_data)
        
        if response.status_code != 200:
            print(f"Error calling Genogram API: {response.text}")
            return None
            
        genogram_json = response.text # レスポンスはそのままJSON文字列として扱う
        
        # 3. JSONを圧縮 (lz-string)
        lz = LZString()
        compressed = lz.compressToEncodedURIComponent(genogram_json)
        
        # 4. URL生成
        full_url = f"{GENOGRAM_EDITOR_URL}?data={compressed}"
        return full_url

    except Exception as e:
        print(f"Exception in generate_genogram_url: {e}")
        return None

import json
import google.generativeai as genai
from lzstring import LZString

# ローカル開発用URL（必要に応じて変更）
# KAOKUZU_EDITOR_URL = "https://genogram-editor.vercel.app/house-plan"
KAOKUZU_EDITOR_URL = "http://localhost:3000/house-plan"

def generate_kaokuzu_url(text: str = "", files: list = None, api_key: str = ""):
    """
    Geminiを使用して家屋図データを生成し、エディタURLを作成する
    """
    try:
        if not api_key:
            print("Error: API Key is missing")
            return None, "API Keyが設定されていません"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-flash-preview")

        system_prompt = """あなたはケアマネージャーの作成する「家屋図（Kaokuzu）」データを生成するAIです。
入力されたアセスメント情報や家の記述から、部屋の配置と家具・設備の配置を推論し、以下のJSON形式で出力してください。

【出力JSON形式】
{
  "scale": 50,
  "rooms": [
    {
      "id": "room_1",
      "name": "居間",
      "type": "Living",
      "x": 50,
      "y": 50,
      "width": 200,
      "height": 200,
      "rotation": 0
    }
  ],
  "furniture": [
    {
      "id": "furn_1",
      "type": "Bed",
      "x": 60,
      "y": 60,
      "width": 0,
      "height": 0,
      "rotation": 0
    }
  ],
  "walls": []
}

【定義データ】
RoomType: "Living", "Kitchen", "Bedroom", "Bathroom", "Toilet", "Entrance", "Corridor", "Other"
FurnitureType: "Bed", "Wheelchair", "Table", "Toilet", "Bath", "Door", "Window", "Stairs", "Handrail"

【配置ルール】
- 座標系: 左上が(0,0)。単位はピクセル。1m = 50px と仮定。
- 部屋の配置: 記述から相対位置（「台所の隣に居間」など）を読み取り、重ならないように配置してください。不明な場合は適当にグリッド状に並べてください。
- 部屋サイズ:
  - 居間(Living): 200x200 (約8畳)
  - 台所(Kitchen): 150x150 (約4.5畳)
  - 寝室(Bedroom): 180x180 (約6畳)
  - トイレ(Toilet): 80x80
  - 浴室(Bath): 100x100
  - 玄関(Entrance): 100x80
- 一般的な日本の住宅を想定してください。
- "walls" 配列は今回は空で構いません（部屋のRectで表現するため）。
- 読み取れる家具（ベッド、ポータブルトイレ、手すり等）は必ず配置してください。特に「介護ベッド」「車椅子」などは重要です。

【入力テキスト】
""" + text + """

JSONのみを出力してください。Markdownのコードブロックは含めないでください。
"""

        prompt_parts = [system_prompt]

        if files:
            for f in files:
                prompt_parts.append({
                    "mime_type": f.type,
                    "data": f.getvalue()
                })

        response = model.generate_content(prompt_parts)
        response_text = response.text.strip()

        # Clean JSON
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_text = response_text

        # Validate JSON (simple check)
        json.loads(json_text)

        # Compress
        lz = LZString()
        compressed = lz.compressToEncodedURIComponent(json_text)

        full_url = f"{KAOKUZU_EDITOR_URL}?data={compressed}"
        return full_url, None

    except Exception as e:
        return None, str(e)

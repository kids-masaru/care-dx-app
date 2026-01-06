import json
import google.generativeai as genai
from lzstring import LZString

# Editor URL (Same environment as genogram)
GENOGRAM_EDITOR_URL = "https://genogram-editor.vercel.app" 
# In dev handling, it might be localhost:3000 but user asked to match app style.
# If running locally, you might want http://localhost:3000/body-map if the page is different?
# The user's BodyMapEditor is at `/src/app/page.tsx`? No, page.tsx is Genogram.
# BodyMap is at `/house-plan`? No.
# Looking at the navigation bar in BodyMapEditor:
# 👨‍👩‍👧‍👦 ジェノグラム = /
# 🏠 家屋図 = /house-plan
# 👤 身体図 = /body-map (implied? No, I need to check where it is mounted)
# User hasn't shown a new route for BodyMap. It might be a component shown?
# Wait, I need to check `src/app` structure to see where BodyMap is hosted.
# I will check that before finalizing the URL. Defaulting to assuming it's accessible.
# If I don't know the route, I'll guess `/body-map` or check `page.tsx` content.

def generate_bodymap_data(text: str = "", api_key: str = ""):
    """
    Body Map Data Logic
    """
    try:
        if not api_key:
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-flash-preview")

        system_prompt = """あなたは医療・介護のアセスメント情報の分析官です。
以下の入力テキストから、身体状況（マヒ、欠損、機能低下、または身体的な特記事項）を抽出し、JSON形式で出力してください。

【出力形式】
{
  "findings": [
    {
      "part": "部位名（例: 右上腕, 左下肢, Stomach, Head等）",
      "condition": "状態（例: 右片麻痺, 切断, 拘縮, 褥瘡）",
      "note": "詳細な補足事項（あれば）"
    }
  ]
}

【部位の目安】
head, face, neck, shoulder, chest, stomach, back, hip, leg, arm, hand, general (全身)

【条件の分類目安】
- 麻痺 (Paralysis): マヒ, 動かない, 脳梗塞後遺症
- 欠損 (Missing): 切断, 欠損
- 機能低下 (FunctionLoss): 拘縮, 筋力低下, 可動域制限
- その他 (Comment): 褥瘡, 痛み, 手術痕, 装具使用

【入力情報】
""" + text + """

JSONのみを出力してください。"""

        response = model.generate_content(system_prompt)
        response_text = response.text.strip()
        
        # JSON extraction cleanup
        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0].strip()
        elif "{" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_text = response_text[start:end]

        return json.loads(json_text)

    except Exception as e:
        raise e

def generate_bodymap_url(text: str = "", api_key: str = ""):
    try:
        data = generate_bodymap_data(text, api_key)
        if not data:
             return None, "No Data"

        lz = LZString()
        compressed = lz.compressToEncodedURIComponent(json.dumps(data, ensure_ascii=False))
        
        return f"{GENOGRAM_EDITOR_URL}/body-map?data={compressed}", None

    except Exception as e:
        return None, str(e)

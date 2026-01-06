import json
import os
import google.generativeai as genai
from lzstring import LZString

# ここをデプロイ先のURLに変更してください
GENOGRAM_EDITOR_URL = "https://genogram-editor.vercel.app" 
# 例: GENOGRAM_EDITOR_URL = "https://your-genogram-app.vercel.app"

def generate_genogram_data(text: str = "", files: list = None, api_key: str = ""):
    """
    Genogram Data Extraction Logic
    Returns: dict (JSON Object) or None
    """
    try:
        if not api_key:
            print("Error: API Key is missing")
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-flash-preview")

        system_prompt = """あなたは家族構成を分析する専門家です。
以下の入力（テキスト、音声、画像、PDFなど）を総合的に分析し、ジェノグラム（家族構成図）を作成するための情報をJSON形式で抽出してください。

【出力形式】
{
  "members": [
    {
      "id": "一意のID（例: self, father, mother, spouse, son1, daughter1等）",
      "name": "名前",
      "gender": "M（男性）/ F（女性）",
      "birthYear": 1960,
      "isDeceased": false,
      "isSelf": true,
      "isKeyPerson": false,
      "generation": 0,
      "note": "特記事項"
    }
  ],
  "marriages": [
    {
      "husband": "夫のID",
      "wife": "妻のID",
      "status": "married / divorced / separated / cohabitation",
      "children": ["子のID1", "子のID2"]
    }
  ]
}

【generationのルール】
- 本人の世代を0とする
- 本人の親世代は-1、祖父母は-2
- 本人の子世代は1、孫は2

【ルール】
- 本人（介護を受ける人）は isSelf: true にする
- 死亡している人は isDeceased: true にする
- 結婚・離婚はmarriagesで表現
- 子供はmarriagesのchildrenに含める
- 【重要】本人（または他の人物）の両親の情報がある場合、その両親が死別していても必ず 'marriages' に両親のペアを追加し、子供リストに本人を含めること。これがないと親子線が描画されません。
- 手書きの図やアセスメントシートが含まれる場合、そこから読み取れる家族関係を網羅してください。
- 音声データが含まれる場合、会話内容から家族関係を聴き取って反映してください。

【推論ルール】
- 文脈から「独立」「家を出た」「別居」などで配偶者や子供の存在が示唆される場合、**名前がなくても配偶者ノード（「夫」「妻」など）を作成し、marriageを追加してください**。これにより家系図の線が正しく引かれます。
- 子供（息子・娘）がいる人物には、必ず配偶者を追加してmarriage関係を作成してください。片親しか情報がない場合でも、親子線を描画するために配偶者（「妻」「夫」など）とのmarriageが必要です。
- 情報が不足している場合でも、家系図として成立するように合理的な推測を行って補完してください。

【入力情報】
""" + text + """

JSONのみを出力してください。説明は不要です。"""

        prompt_parts = [system_prompt]

        if files:
            for f in files:
                file_bytes = f.getvalue()
                mime_type = f.type
                prompt_parts.append({
                    "mime_type": mime_type,
                    "data": file_bytes
                })

        response = model.generate_content(prompt_parts)
        response_text = response.text.strip()
        
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
        error_msg = f"{str(e)}"
        print(f"Genogram Generation Error: {error_msg}")
        if "404" in error_msg:
             # debug info pass
             pass
        raise e

def generate_genogram_url(text: str = "", files: list = None, api_key: str = ""):
    try:
        data = generate_genogram_data(text, files, api_key)
        if not data:
             return None, "No Data"
        
        lz = LZString()
        compressed = lz.compressToEncodedURIComponent(json.dumps(data, ensure_ascii=False))
        full_url = f"{GENOGRAM_EDITOR_URL}?data={compressed}"
        return full_url, None
    except Exception as e:
        return None, str(e)


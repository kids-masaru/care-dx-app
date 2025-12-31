"""
ジェノグラム（家族構成図）作成ロジック
Gemini APIで情報を抽出し、Graphvizで描画

正しいジェノグラムのルール:
- 男性 = □（四角）、女性 = ○（丸）
- 本人 = 二重枠
- 死亡者 = ×印を重ねる（枠内に×）
- 結婚 = 実線で横につなぐ
- 離婚 = 線の上に // 
- 同世代は横に並ぶ
- 子供は親の下にぶら下がる
"""
import json
import re
import graphviz


def get_genogram_data_from_gemini(model, text_input):
    """
    Gemini APIを使用して、入力テキストからジェノグラム用JSONデータを抽出
    
    Args:
        model: Geminiモデルオブジェクト（google.generativeai）
        text_input: ユーザーが入力した家族構成の説明文
    
    Returns:
        dict: ジェノグラム描画用のJSONデータ
    """
    prompt = """あなたは家族構成を分析する専門家です。
以下の文章から、ジェノグラム（家族構成図）を作成するための情報をJSON形式で抽出してください。

【出力形式】
```json
{
  "members": [
    {
      "id": "一意のID（例: self, father, mother, spouse, son1, daughter1等）",
      "name": "名前",
      "gender": "M（男性）/ F（女性）",
      "birth_year": 1960,
      "death_year": 2020,
      "is_self": true,
      "is_deceased": false,
      "generation": 0,
      "note": "特記事項（認知症、要介護等）"
    }
  ],
  "marriages": [
    {
      "husband": "夫のID",
      "wife": "妻のID",
      "status": "married / divorced",
      "children": ["子のID1", "子のID2"]
    }
  ]
}
```

【generationのルール】
- 本人の世代を0とする
- 本人の親世代は-1、祖父母は-2
- 本人の子世代は1、孫は2

【ルール】
- 本人（介護を受ける人）は `is_self: true` にする
- 死亡している人は `is_deceased: true` にする
- 結婚・離婚はmarriagesで表現
- 子供はmarriagesのchildrenに含める

【入力文章】
""" + text_input + """

JSONのみを出力してください。説明は不要です。
"""
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # デバッグ情報を収集
        debug_info = {
            "raw_response_length": len(raw_text),
            "raw_response_preview": raw_text[:500] if len(raw_text) > 500 else raw_text,
        }
        
        text = raw_text
        
        # JSONブロックを抽出（複数パターン対応）
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1).strip()
            debug_info["extraction_method"] = "pattern1_json_block"
        else:
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
            if json_match:
                text = json_match.group(1).strip()
                debug_info["extraction_method"] = "pattern2_code_block"
            else:
                json_match = re.search(r'(\{[\s\S]*\})', text)
                if json_match:
                    text = json_match.group(1).strip()
                    debug_info["extraction_method"] = "pattern3_braces"
                else:
                    debug_info["extraction_method"] = "no_match"
        
        debug_info["extracted_json_preview"] = text[:300] if len(text) > 300 else text
        
        data = json.loads(text)
        data["_debug"] = debug_info
        return data
    except json.JSONDecodeError as e:
        return {
            "error": f"JSONパースエラー: {str(e)}", 
            "members": [], 
            "marriages": [],
            "_debug": {
                "error_type": "JSONDecodeError",
                "raw_response": raw_text[:1000] if 'raw_text' in locals() else "N/A",
                "extracted_text": text[:500] if 'text' in locals() else "N/A"
            }
        }
    except Exception as e:
        return {
            "error": str(e), 
            "members": [], 
            "marriages": [],
            "_debug": {"error_type": type(e).__name__, "details": str(e)}
        }


def create_genogram_graph(data):
    """
    JSONデータからGraphviz Digraphオブジェクトを作成
    正しいジェノグラムのルールに従う
    """
    dot = graphviz.Graph(comment='Genogram', engine='dot')
    dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='0.8')
    dot.attr('node', fontname='Meiryo', fontsize='10')
    dot.attr('edge', fontname='Meiryo')
    
    members = data.get('members', [])
    marriages = data.get('marriages', [])
    
    # メンバーをIDでインデックス化
    member_dict = {m.get('id', ''): m for m in members}
    
    # 世代ごとにグループ化
    generations = {}
    for member in members:
        gen = member.get('generation', 0)
        if gen not in generations:
            generations[gen] = []
        generations[gen].append(member)
    
    # 結婚ポイント（夫婦をつなぐ中間ノード）のカウンター
    marriage_point_counter = 0
    
    # メンバーのノード作成
    for member in members:
        member_id = str(member.get('id', '') or 'unknown')
        name = member.get('name') or '不明'
        gender = member.get('gender') or 'U'
        is_self = member.get('is_self', False)
        is_deceased = member.get('is_deceased', False) or member.get('death_year')
        note = member.get('note') or ''
        birth_year = member.get('birth_year')
        
        # ラベル作成
        label = str(name)
        if birth_year:
            label += f"\n({birth_year})"
        if note:
            label += f"\n[{note}]"
        
        # 形状の決定（男性=box、女性=circle）
        if gender == 'M':
            shape = 'box'
            width = '0.5'
            height = '0.5'
        elif gender == 'F':
            shape = 'circle'
            width = '0.5'
            height = '0.5'
        else:
            shape = 'diamond'
            width = '0.4'
            height = '0.4'
        
        # 死亡者の表現（×印を入れる）
        if is_deceased:
            # 死亡者はラベルに×を追加
            label = f"×\n{label}"
            style = 'solid'
            fillcolor = 'white'
        else:
            style = 'solid'
            fillcolor = 'white'
        
        # 本人は二重枠
        peripheries = '2' if is_self else '1'
        penwidth = '2' if is_self else '1'
        
        dot.node(
            member_id,
            label=label,
            shape=shape,
            style=style,
            fillcolor=fillcolor,
            peripheries=peripheries,
            penwidth=penwidth,
            width=width,
            height=height,
            fixedsize='false'
        )
    
    # 世代ごとにサブグラフで横並びにする
    for gen in sorted(generations.keys()):
        with dot.subgraph() as s:
            s.attr(rank='same')
            for member in generations[gen]:
                s.node(str(member.get('id', '')))
    
    # 結婚関係の描画
    for marriage in marriages:
        husband_id = str(marriage.get('husband', ''))
        wife_id = str(marriage.get('wife', ''))
        status = marriage.get('status', 'married')
        children = marriage.get('children', [])
        
        if husband_id and wife_id:
            # 結婚ポイント（中間ノード）を作成
            marriage_point = f"m{marriage_point_counter}"
            marriage_point_counter += 1
            
            # 結婚ポイントは見えない小さなノード
            dot.node(marriage_point, label='', shape='point', width='0.1', height='0.1')
            
            # 夫婦を結婚ポイントに接続
            if status == 'divorced':
                # 離婚は破線
                dot.edge(husband_id, marriage_point, style='solid', dir='none')
                dot.edge(marriage_point, wife_id, style='solid', dir='none', label='//')
            else:
                # 結婚は実線
                dot.edge(husband_id, marriage_point, style='solid', dir='none')
                dot.edge(marriage_point, wife_id, style='solid', dir='none')
            
            # 夫婦を同じランクに
            with dot.subgraph() as s:
                s.attr(rank='same')
                s.node(husband_id)
                s.node(wife_id)
                s.node(marriage_point)
            
            # 子供を結婚ポイントからぶら下げる
            for child_id in children:
                child_id = str(child_id)
                if child_id in member_dict:
                    dot.edge(marriage_point, child_id, style='solid', dir='none')
    
    return dot


def render_genogram_svg(data):
    """
    ジェノグラムをSVG文字列として出力
    """
    try:
        graph = create_genogram_graph(data)
        return graph.pipe(format='svg').decode('utf-8')
    except Exception as e:
        return f"<p style='color:red'>描画エラー: {e}</p>"

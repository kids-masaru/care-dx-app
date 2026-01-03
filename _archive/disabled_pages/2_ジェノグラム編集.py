"""
ジェノグラム（家族構成図）インタラクティブエディタ
streamlit-agraphを使用してドラッグ&ドロップ編集を可能に
"""
import streamlit as st
import os
import sys
import json
import uuid

# ルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import google.generativeai as genai
from streamlit_agraph import agraph, Node, Edge, Config
from utils.genogram_maker import get_genogram_data_from_gemini

# 環境変数読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="ジェノグラム編集 | 介護DX",
    page_icon="✏️",
    layout="wide"
)

st.title("✏️ ジェノグラム インタラクティブエディタ")
st.caption("ドラッグ&ドロップでノードを移動、クリックで編集できます")

# APIキー取得
def get_api_key():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except:
            pass
    if not api_key:
        with st.sidebar:
            st.markdown("### 🔑 APIキー設定")
            api_key = st.text_input("Gemini APIキー", type="password")
    return api_key


# セッションステート初期化
if 'genogram_nodes' not in st.session_state:
    st.session_state.genogram_nodes = []
if 'genogram_edges' not in st.session_state:
    st.session_state.genogram_edges = []
if 'genogram_data' not in st.session_state:
    st.session_state.genogram_data = None
if 'selected_node' not in st.session_state:
    st.session_state.selected_node = None


def data_to_agraph(data):
    """ジェノグラムデータをagraph用のノードとエッジに変換"""
    nodes = []
    edges = []
    
    members = data.get('members', [])
    marriages = data.get('marriages', [])
    
    # メンバーをノードに変換
    for member in members:
        member_id = str(member.get('id', ''))
        name = member.get('name') or '不明'
        gender = member.get('gender') or 'U'
        is_self = member.get('is_self', False)
        is_deceased = member.get('is_deceased', False)
        birth_year = member.get('birth_year')
        note = member.get('note', '')
        generation = member.get('generation', 0)
        
        # ラベル作成
        label = name
        if birth_year:
            label += f"\n({birth_year})"
        if is_deceased:
            label = f"×{label}"
        if note:
            label += f"\n[{note}]"
        
        # 色と形状
        if gender == 'M':
            shape = 'box'
            color = '#4A90D9' if is_self else '#87CEEB'
        elif gender == 'F':
            shape = 'circle' if not is_deceased else 'circularImage'
            color = '#FF69B4' if is_self else '#FFB6C1'
        else:
            shape = 'diamond'
            color = '#90EE90'
        
        # 死亡者はグレー
        if is_deceased:
            color = '#808080'
        
        # 本人は太枠
        border_width = 4 if is_self else 2
        
        nodes.append(Node(
            id=member_id,
            label=label,
            shape=shape,
            color=color,
            size=40,
            borderWidth=border_width,
            font={'size': 12, 'face': 'Meiryo'},
            title=json.dumps(member, ensure_ascii=False)
        ))
    
    # 結婚関係をエッジに変換
    marriage_counter = 0
    for marriage in marriages:
        husband_id = str(marriage.get('husband', ''))
        wife_id = str(marriage.get('wife', ''))
        status = marriage.get('status', 'married')
        children = marriage.get('children', [])
        
        if husband_id and wife_id:
            # 結婚ポイントノード
            mp_id = f"marriage_{marriage_counter}"
            marriage_counter += 1
            
            nodes.append(Node(
                id=mp_id,
                label='',
                shape='dot',
                size=5,
                color='#000000'
            ))
            
            # 夫婦-結婚ポイントのエッジ
            edge_style = 'dashed' if status == 'divorced' else None
            label = '//' if status == 'divorced' else ''
            
            edges.append(Edge(source=husband_id, target=mp_id, color='#333333', width=2, dashes=status=='divorced'))
            edges.append(Edge(source=mp_id, target=wife_id, color='#333333', width=2, label=label, dashes=status=='divorced'))
            
            # 子供へのエッジ
            for child_id in children:
                edges.append(Edge(source=mp_id, target=str(child_id), color='#333333', width=2))
    
    return nodes, edges


# サイドバー
with st.sidebar:
    st.markdown("### 📌 操作方法")
    st.markdown("""
    - **ドラッグ**: ノードを移動
    - **クリック**: ノードを選択して編集
    - **ホイール**: ズームイン/アウト
    """)
    
    st.markdown("---")
    st.markdown("### ➕ ノード追加")
    
    new_name = st.text_input("名前")
    new_gender = st.selectbox("性別", ["M（男性）", "F（女性）", "U（不明）"])
    new_birth = st.text_input("生年（例: 1960）")
    new_is_self = st.checkbox("本人")
    new_is_deceased = st.checkbox("死亡")
    new_note = st.text_input("備考")
    
    if st.button("➕ ノード追加", use_container_width=True):
        new_node = {
            "id": f"node_{uuid.uuid4().hex[:8]}",
            "name": new_name or "新規",
            "gender": new_gender[0],
            "birth_year": int(new_birth) if new_birth.isdigit() else None,
            "is_self": new_is_self,
            "is_deceased": new_is_deceased,
            "note": new_note,
            "generation": 0
        }
        if st.session_state.genogram_data:
            st.session_state.genogram_data['members'].append(new_node)
            nodes, edges = data_to_agraph(st.session_state.genogram_data)
            st.session_state.genogram_nodes = nodes
            st.session_state.genogram_edges = edges
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 🔗 関係追加")
    
    if st.session_state.genogram_data:
        member_ids = [m.get('id', '') for m in st.session_state.genogram_data.get('members', [])]
        member_names = {m.get('id', ''): m.get('name', '不明') for m in st.session_state.genogram_data.get('members', [])}
        
        if len(member_ids) >= 2:
            rel_from = st.selectbox("夫", member_ids, format_func=lambda x: member_names.get(x, x))
            rel_to = st.selectbox("妻", member_ids, format_func=lambda x: member_names.get(x, x))
            rel_status = st.selectbox("状態", ["married（結婚中）", "divorced（離婚）"])
            rel_children = st.multiselect("子供", member_ids, format_func=lambda x: member_names.get(x, x))
            
            if st.button("🔗 結婚関係追加", use_container_width=True):
                new_marriage = {
                    "husband": rel_from,
                    "wife": rel_to,
                    "status": rel_status.split("（")[0],
                    "children": rel_children
                }
                if 'marriages' not in st.session_state.genogram_data:
                    st.session_state.genogram_data['marriages'] = []
                st.session_state.genogram_data['marriages'].append(new_marriage)
                nodes, edges = data_to_agraph(st.session_state.genogram_data)
                st.session_state.genogram_nodes = nodes
                st.session_state.genogram_edges = edges
                st.rerun()


# メインエリア
col_input, col_graph = st.columns([1, 2])

with col_input:
    st.markdown("### 📝 家族構成の説明")
    
    sample_text = """本人は田中太郎（65歳、男性）。妻の田中花子（62歳）と同居。
長男の田中一郎（38歳）は結婚して独立、妻と子供2人あり。
長女の田中美咲（35歳）は離婚して実家に戻ってきている。
本人の父は3年前に他界、母（88歳）は施設入所中で認知症あり。"""
    
    family_text = st.text_area("家族構成を入力", value=sample_text, height=150)
    
    api_key = get_api_key()
    
    if api_key:
        if st.button("🎨 AI生成", type="primary", use_container_width=True):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")
                
                with st.spinner("AIが分析中..."):
                    data = get_genogram_data_from_gemini(model, family_text)
                    
                    if data.get("error"):
                        st.error(f"エラー: {data['error']}")
                    else:
                        st.session_state.genogram_data = data
                        nodes, edges = data_to_agraph(data)
                        st.session_state.genogram_nodes = nodes
                        st.session_state.genogram_edges = edges
                        st.success("✅ 生成完了！右のエディタで編集できます")
            except Exception as e:
                st.error(f"エラー: {e}")
    else:
        st.warning("APIキーを設定してください")
    
    st.markdown("---")
    
    # JSON表示・編集
    if st.session_state.genogram_data:
        with st.expander("📋 JSONデータ", expanded=False):
            json_str = json.dumps(st.session_state.genogram_data, ensure_ascii=False, indent=2)
            edited_json = st.text_area("JSON編集", value=json_str, height=300)
            
            if st.button("JSONから更新"):
                try:
                    new_data = json.loads(edited_json)
                    st.session_state.genogram_data = new_data
                    nodes, edges = data_to_agraph(new_data)
                    st.session_state.genogram_nodes = nodes
                    st.session_state.genogram_edges = edges
                    st.success("更新しました")
                    st.rerun()
                except:
                    st.error("JSONが不正です")

with col_graph:
    st.markdown("### 📊 ジェノグラム（ドラッグで編集）")
    
    if st.session_state.genogram_nodes:
        # agraph設定（vis.js準拠）
        config = Config(
            width=800,
            height=600,
            directed=False,
            physics=False,
            hierarchical=False,
        )
        
        # グラフ表示
        selected = agraph(
            nodes=st.session_state.genogram_nodes,
            edges=st.session_state.genogram_edges,
            config=config
        )
        
        if selected:
            st.session_state.selected_node = selected
            st.info(f"選択中: {selected}")
            
            # 選択されたノードの編集
            if st.session_state.genogram_data:
                for member in st.session_state.genogram_data.get('members', []):
                    if member.get('id') == selected:
                        st.markdown("#### 選択ノードの編集")
                        col1, col2 = st.columns(2)
                        with col1:
                            member['name'] = st.text_input("名前", value=member.get('name', ''))
                            member['gender'] = st.selectbox("性別", ["M", "F", "U"], 
                                                           index=["M", "F", "U"].index(member.get('gender', 'U')))
                        with col2:
                            member['is_deceased'] = st.checkbox("死亡", value=member.get('is_deceased', False))
                            member['is_self'] = st.checkbox("本人", value=member.get('is_self', False))
                        
                        if st.button("✅ 更新", key="update_node"):
                            nodes, edges = data_to_agraph(st.session_state.genogram_data)
                            st.session_state.genogram_nodes = nodes
                            st.session_state.genogram_edges = edges
                            st.rerun()
                        
                        if st.button("🗑️ 削除", key="delete_node"):
                            st.session_state.genogram_data['members'] = [
                                m for m in st.session_state.genogram_data['members'] 
                                if m.get('id') != selected
                            ]
                            nodes, edges = data_to_agraph(st.session_state.genogram_data)
                            st.session_state.genogram_nodes = nodes
                            st.session_state.genogram_edges = edges
                            st.rerun()
                        break
    else:
        st.info("左側で「AI生成」ボタンを押してジェノグラムを作成してください")
        st.markdown("""
        <div style="
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 100px 50px;
            text-align: center;
            color: #888;
            background: #f9f9f9;
        ">
            <p style="font-size: 48px; margin: 0;">✏️</p>
            <p>ここにインタラクティブなジェノグラムが表示されます</p>
        </div>
        """, unsafe_allow_html=True)

# フッター
st.markdown("---")
st.caption("💡 ノードをドラッグして位置を調整できます。クリックで選択して編集・削除ができます。")

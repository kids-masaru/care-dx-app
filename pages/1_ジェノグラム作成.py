"""
ジェノグラム（家族構成図）作成ページ
Streamlit Pagesとして実装
"""
import streamlit as st
import os
import sys
import json

# ルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import google.generativeai as genai
from utils.genogram_maker import get_genogram_data_from_gemini, create_genogram_graph, render_genogram_svg

# 環境変数読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="ジェノグラム作成 | 介護DX",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide"
)

st.title("👨‍👩‍👧‍👦 ジェノグラム（家族構成図）作成")
st.caption("家族構成の説明文から、自動でジェノグラムを作成します")

# APIキー取得
def get_api_key():
    """APIキーを取得（.env、secrets、サイドバー入力の優先順）"""
    # 1. 環境変数
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    # 2. Streamlit secrets
    if not api_key:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except:
            pass
    
    # 3. サイドバーから入力
    if not api_key:
        with st.sidebar:
            st.markdown("### 🔑 APIキー設定")
            api_key = st.text_input(
                "Gemini APIキー",
                type="password",
                help="Google AI StudioでAPIキーを取得してください"
            )
    
    return api_key


# サイドバー設定
with st.sidebar:
    st.markdown("### 📌 使い方")
    st.markdown("""
    1. 左側に家族構成の説明を入力
    2. 「ジェノグラム生成」ボタンをクリック
    3. 右側にジェノグラムが表示されます
    
    **記号の意味:**
    - □ = 男性
    - ○ = 女性
    - ◇ = 性別不明
    - 二重枠 = 本人
    - グレー = 死亡
    - // = 離婚
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ オプション")
    show_json = st.checkbox("JSONデータを表示/編集", value=False)


api_key = get_api_key()

if not api_key:
    st.warning("⚠️ Gemini APIキーを設定してください（サイドバーまたは環境変数）")
    st.stop()

# Geminiモデル設定
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    st.error(f"Gemini APIの設定に失敗しました: {e}")
    st.stop()

# セッションステート初期化
if 'genogram_data' not in st.session_state:
    st.session_state.genogram_data = None
if 'genogram_json' not in st.session_state:
    st.session_state.genogram_json = ""

# メインエリア（2カラム）
col_input, col_output = st.columns([1, 1])

with col_input:
    st.markdown("### 📝 家族構成の説明")
    
    # サンプルテキスト
    sample_text = """本人は田中太郎（65歳、男性）。妻の田中花子（62歳）と同居。
長男の田中一郎（38歳）は結婚して独立、妻と子供2人あり。
長女の田中美咲（35歳）は離婚して実家に戻ってきている。
本人の父は3年前に他界、母（88歳）は施設入所中で認知症あり。"""
    
    family_text = st.text_area(
        "家族構成を自由に記述してください",
        value=sample_text,
        height=200,
        help="例：「本人は〇〇さん（80歳、女性）。夫は5年前に他界。長男と同居中。」"
    )
    
    if st.button("🎨 ジェノグラム生成", type="primary", use_container_width=True):
        if family_text.strip():
            with st.spinner("AIが家族構成を分析中..."):
                try:
                    data = get_genogram_data_from_gemini(model, family_text)
                    
                    if data.get("error"):
                        st.error(f"エラー: {data['error']}")
                        # デバッグ情報を表示
                        if "_debug" in data:
                            with st.expander("🔍 デバッグ情報", expanded=True):
                                st.json(data["_debug"])
                    else:
                        st.session_state.genogram_data = data
                        st.session_state.genogram_json = json.dumps(data, ensure_ascii=False, indent=2)
                        st.success("✅ ジェノグラムを生成しました！")
                        # デバッグ情報を表示（成功時も）
                        if "_debug" in data:
                            with st.expander("🔍 デバッグ情報"):
                                st.json(data["_debug"])
                        st.rerun()
                except Exception as e:
                    st.error(f"生成エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.warning("家族構成の説明を入力してください")
    
    # JSON編集エリア（オプション）
    if show_json and st.session_state.genogram_json:
        st.markdown("---")
        st.markdown("### 🔧 JSONデータ編集")
        st.caption("AIが抽出したデータを手動で修正できます")
        
        edited_json = st.text_area(
            "JSONデータ",
            value=st.session_state.genogram_json,
            height=300
        )
        
        if st.button("📐 JSONから再描画"):
            try:
                new_data = json.loads(edited_json)
                st.session_state.genogram_data = new_data
                st.session_state.genogram_json = edited_json
                st.success("JSONを更新しました！")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"JSONの形式が不正です: {e}")

with col_output:
    st.markdown("### 📊 ジェノグラム")
    
    if st.session_state.genogram_data:
        try:
            graph = create_genogram_graph(st.session_state.genogram_data)
            
            # SVGとして描画
            st.graphviz_chart(graph, use_container_width=True)
            
            # ダウンロード機能
            st.markdown("---")
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # SVG出力
                try:
                    svg_data = graph.pipe(format='svg').decode('utf-8')
                    st.download_button(
                        "📥 SVGダウンロード",
                        data=svg_data,
                        file_name="genogram.svg",
                        mime="image/svg+xml",
                        use_container_width=True
                    )
                except:
                    st.info("SVGダウンロードには環境設定が必要です")
            
            with col_dl2:
                # JSONダウンロード
                st.download_button(
                    "📥 JSONダウンロード",
                    data=json.dumps(st.session_state.genogram_data, ensure_ascii=False, indent=2),
                    file_name="genogram_data.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            # 抽出されたメンバー一覧
            with st.expander("👥 抽出されたメンバー一覧"):
                members = st.session_state.genogram_data.get('members', [])
                for m in members:
                    gender_icon = "👨" if m.get('gender') == 'M' else "👩" if m.get('gender') == 'F' else "👤"
                    self_badge = "【本人】" if m.get('is_self') else ""
                    deceased = "（没）" if m.get('is_deceased') or m.get('death_year') else ""
                    gen = m.get('generation', 0)
                    gen_label = f"[世代{gen}]" if gen != 0 else "[本人世代]"
                    st.write(f"{gender_icon} {m.get('name', '不明')}{self_badge}{deceased} {gen_label}")
            
        except Exception as e:
            st.error(f"描画エラー: {e}")
            st.info("Graphvizがインストールされていない場合、SVG描画に失敗することがあります。")
    else:
        st.info("左側で家族構成を入力し、「ジェノグラム生成」ボタンを押してください")
        
        # プレースホルダー画像
        st.markdown("""
        <div style="
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 50px;
            text-align: center;
            color: #888;
            background: #f9f9f9;
        ">
            <p style="font-size: 48px; margin: 0;">👨‍👩‍👧‍👦</p>
            <p>ここにジェノグラムが表示されます</p>
        </div>
        """, unsafe_allow_html=True)


# フッター
st.markdown("---")
st.caption("💡 ジェノグラムは家族の関係性を視覚化するツールです。介護計画やケアプラン作成に活用できます。")

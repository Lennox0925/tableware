import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import plotly.express as px

# --- 核心配置 ---
# 請在此處貼上您的 GAS Web App URL
GAS_URL = "https://script.google.com/macros/s/AKfycbxhvUl-BHXp3daZzbEVp3k27QBBfqU_qy_W3QNwtXBuPdeYHnuknBZKedEw486hrcPUbg/exec"

st.set_page_config(layout="wide", page_title="餐具雲端盤點系統", page_icon="🍴")

# --- 平板介面 CSS 優化 ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 60px; font-size: 1.2rem; border-radius: 12px; font-weight: bold; }
    .stNumberInput input { font-size: 1.5rem !important; text-align: center; }
    [data-testid="stSidebar"] { background-color: #1e272e; color: white; }
    .main { background-color: #f1f2f6; }
    div[data-baseweb="select"] > div { font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 側邊欄：左框架導覽 ---
with st.sidebar:
    st.title("店鋪餐具管理")
    st.write(f"📅 今日日期：{datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    
    menu = st.radio(
        "功能選單", 
        ["1. 餐具清單上下載更新", "2. 餐具盤點與破損登記", "3. 數據分析看板"],
        index=0
    )
    
    st.divider()
    # 同步功能：將本機暫存上傳至雲端 GAS
    if st.button("🚀 同步暫存至雲端"):
        if 'damage_buffer' in st.session_state and st.session_state.damage_buffer:
            try:
                payload = {"action": "sync_damage", "data": st.session_state.damage_buffer}
                res = requests.post(GAS_URL, json=payload)
                if res.status_code == 200:
                    st.success(f"同步成功：{res.text}")
                    st.session_state.damage_buffer = [] # 清空暫存
                else:
                    st.error("同步失敗，請檢查網路")
            except Exception as e:
                st.error(f"連線錯誤: {e}")
        else:
            st.info("目前無待同步的資料")

# --- 右框架：功能內容 ---

# 功能 1：餐具清單上下載更新
if menu == "1. 餐具清單上下載更新":
    st.header("📋 餐具清單初始化")
    st.write("請上傳 CSV 檔，格式應包含：**餐具品項、單位、安全庫存量、店鋪使用量**")
    
    file = st.file_uploader("選擇餐具清單 CSV", type="csv")
    if file:
        try:
            df_master = pd.read_csv(file, encoding='utf-8-sig')
        except UnicodeDecodeError:
    # 如果 utf-8 失敗，嘗試繁體中文常用的 big5
    df_master = pd.read_csv(file, encoding='big5')
        st.subheader("預覽清單內容")
        st.dataframe(df_master, use_container_width=True, hide_index=True)
        
        if st.button("確認上傳至雲端"):
            # 轉換為 GAS 接受的二維陣列格式
            data_list = [df_master.columns.tolist()] + df_master.values.tolist()
            payload = {"action": "update_master_list", "data": data_list}
            res = requests.post(GAS_URL, json=payload)
            st.success("✅ 雲端 Master 清單已建立！")

# 功能 2：餐具盤點與破損登記
elif menu == "2. 餐具盤點與破損登記":
    st.header("📝 每日紀錄與月度盤點")
    
    tab_damage, tab_inventory = st.tabs(["💔 破損登記 (暫存)", "📅 月度盤點提交"])
    
    # --- A. 破損登記 (本機暫存) ---
    with tab_damage:
        st.write("此處紀錄會先存於本機，需點擊左側「同步」才會傳至雲端。")
        with st.form("damage_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                d_item = st.text_input("餐具品項", placeholder="請輸入名稱")
            with col2:
                # 數量輸入：無預設值(None)，確保為整數
                d_qty = st.number_input("破損數量", min_value=1, step=1, value=None)
            with col3:
                d_reason = st.selectbox("破損原因", ["(請選擇)", "洗滌損壞", "人員疏失", "客人打破", "自然耗損"], index=0)
            
            if st.form_submit_button("新增至暫存"):
                if d_item and d_qty and d_reason != "(請選擇)":
                    if 'damage_buffer' not in st.session_state:
                        st.session_state.damage_buffer = []
                    
                    new_entry = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "item": d_item,
                        "qty": int(d_qty),
                        "reason": d_reason
                    }
                    st.session_state.damage_buffer.append(new_entry)
                    st.toast(f"已暫存: {d_item} {d_qty}個")
                else:
                    st.error("請完整填寫品項、數量與原因")

        if 'damage_buffer' in st.session_state and st.session_state.damage_buffer:
            st.write("📍 **待同步清單：**")
            st.table(pd.DataFrame(st.session_state.damage_buffer))

    # --- B. 月度盤點提交 ---
    with tab_inventory:
        st.subheader(f"{datetime.now().month}月 盤點試算提交")
        st.caption("公式：當月破損量 = (上月盤點總量 + 當月進貨量) - 當月盤點總量")
        
        # 建立盤點表格 (供店鋪修改店鋪使用量與輸入實盤數)
        # 這裡建議手動輸入，或從 Master List 撈取
        inv_df = pd.DataFrame({
            "盤點日期": [datetime.now().strftime("%Y-%m-%d")],
            "餐具品項": [""],
            "上月盤點總數量": [0],
            "當月進貨數量": [0],
            "當月盤點總數量": [0],
            "店鋪使用量": [0],
            "安全庫存量": [0]
        })
        
        # 使用 data_editor 讓表格可編輯
        edited_df = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        
        if st.button("✅ 提交月度盤點至雲端檔案"):
            # 計算當月破損量並重組資料格式
            # (此處可加入 Python 計算邏輯再傳送)
            data_to_send = [edited_df.columns.tolist()] + edited_df.values.tolist()
            payload = {"action": "submit_inventory", "data": data_to_send}
            res = requests.post(GAS_URL, json=payload)
            st.success(f"已建立 {datetime.now().year} 年 {datetime.now().month} 月盤點 Sheet")

# 功能 3：數據分析看板
elif menu == "3. 數據分析看板":
    st.header("📊 破損分析 (Top 5)")
    
    # 這裡未來應從 GAS 抓取當年破損紀錄檔進行分析
    # 以下為模擬數據展示圖表功能
    mock_items = pd.DataFrame({"品項": ["陶瓷盤", "玻璃杯", "咖啡匙", "紅酒杯", "湯碗"], "數量": [15, 12, 8, 5, 3]})
    mock_reasons = pd.DataFrame({"原因": ["洗滌損壞", "客損", "員工疏失", "自然耗損", "其他"], "次數": [20, 10, 5, 3, 2]})

    col_left, col_right = st.columns(2)
    
    with col_left:
        fig_item = px.bar(mock_items, x='數量', y='品項', orientation='h', title="破損品項排行榜 Top 5", color='數量', color_continuous_scale='Reds')
        st.plotly_chart(fig_item, use_container_width=True)
        
    with col_right:
        fig_reason = px.pie(mock_reasons, values='次數', names='原因', title="破損原因分佈 Top 5", hole=0.4)
        st.plotly_chart(fig_reason, use_container_width=True)

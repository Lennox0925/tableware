import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import plotly.express as px

# --- 核心配置 ---
# 請在此處貼上您的 GAS Web App URL，或使用 st.secrets["GAS_URL"]
GAS_URL = "https://script.google.com/macros/s/AKfycbxhvUl-BHXp3daZzbEVp3k27QBBfqU_qy_W3QNwtXBuPdeYHnuknBZKedEw486hrcPUbg/exec"

st.set_page_config(layout="wide", page_title="餐具雲端盤點系統", page_icon="🍴")

# --- 平板介面 CSS 優化 ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 70px; font-size: 1.2rem; border-radius: 12px; font-weight: bold; }
    .stNumberInput input { font-size: 1.5rem !important; text-align: center; }
    [data-testid="stSidebar"] { background-color: #1e272e; color: white; min-width: 260px; }
    .main { background-color: #f1f2f6; }
    div[data-baseweb="select"] > div { font-size: 1.2rem; }
    /* 加大表格字體 */
    .stDataFrame { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 側邊欄：左框架導覽 ---
with st.sidebar:
    st.title("店鋪餐具管理")
    st.info(f"📅 系統日期：{datetime.now().strftime('%Y-%m-%d')}")
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
                    st.success(f"同步完畢！雲端已紀錄。")
                    st.session_state.damage_buffer = [] # 清空暫存
                    st.rerun()
                else:
                    st.error("同步失敗，請檢查網路連線")
            except Exception as e:
                st.error(f"連線錯誤: {e}")
        else:
            st.info("目前無待同步的資料")

# --- 右框架：功能內容 ---

# 功能 1：餐具清單上下載更新 (Master 檔初始化)
if menu == "1. 餐具清單上下載更新":
    st.header("📋 餐具清單初始化")
    st.write("請上傳 CSV 檔，包含欄位：**餐具品項、單位、安全庫存量、店鋪使用量**")
    
    file = st.file_uploader("選擇餐具清單 CSV", type="csv")
    if file:
        try:
            # 處理編碼問題與指標重置
            file.seek(0)
            df_master = pd.read_csv(file, encoding='utf-8-sig')
        except Exception:
            file.seek(0)
            df_master = pd.read_csv(file, encoding='big5')
            
        st.subheader("預覽清單內容")
        st.dataframe(df_master, use_container_width=True, hide_index=True)
        
        if st.button("🚀 確認上傳並更新雲端"):
            # 轉換為 GAS 接受的二維陣列格式
            data_list = [df_master.columns.tolist()] + df_master.values.tolist()
            payload = {"action": "update_master_list", "data": data_list}
            try:
                res = requests.post(GAS_URL, json=payload)
                st.success(f"✅ 雲端回應: {res.text}")
            except Exception as e:
                st.error(f"上傳失敗: {e}")

# 功能 2：餐具盤點與破損登記
elif menu == "2. 餐具盤點與破損登記":
    st.header("📝 每日紀錄與月度盤點")
    
    tab_damage, tab_inventory = st.tabs(["💔 破損登記 (本機暫存)", "📅 月度盤點提交"])
    
    # --- A. 破損登記 (本機暫存，支援平板輸入) ---
    with tab_damage:
        st.write("此處紀錄會先存於本機，需點擊左側「同步」才會傳至雲端。")
        with st.form("damage_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                d_item = st.text_input("餐具品項", placeholder="請輸入名稱")
            with col2:
                # 數量：無預設值，必須手動輸入
                d_qty = st.number_input("破損數量", min_value=1, step=1, value=None)
            with col3:
                d_reason = st.selectbox("破損原因", ["(請選擇)", "洗滌損壞", "人員疏失", "客人打破", "自然耗損"], index=0)
            
            if st.form_submit_button("➕ 新增至暫存區"):
                if d_item and d_qty is not None and d_reason != "(請選擇)":
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
                    st.error("請確認所有欄位已填寫 (數量不可為空)")

        if 'damage_buffer' in st.session_state and st.session_state.damage_buffer:
            st.write("📍 **本機待同步清單：**")
            st.table(pd.DataFrame(st.session_state.damage_buffer))

    # --- B. 月度盤點提交 (產出按月分頁的 Sheet) ---
    with tab_inventory:
        curr_year = datetime.now().year
        curr_month = datetime.now().month
        st.subheader(f"📅 {curr_year} 年 {curr_month} 月 盤點試算")
        st.caption("公式：上月盤點 + 進貨 - 當月盤點 = 當月破損量")
        
        # 建立盤點用動態表格
        inv_df = pd.DataFrame({
            "盤點日期": [datetime.now().strftime("%Y-%m-%d")],
            "餐具品項": [""],
            "當月破損量": [0], # 這裡可由系統計算或手動填入
            "盤點總數量": [None],
            "店鋪使用量": [None],
            "進貨數量": [None],
            "安全庫存量": [None]
        })
        
        # 店鋪使用量在此表格中是可編輯的
        edited_df = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        
        if st.button(f"💾 提交至雲端 {curr_year} 年盤點檔案"):
            # 轉換為 GAS 陣列格式
            data_to_send = [edited_df.columns.tolist()] + edited_df.fillna("").values.tolist()
            payload = {
                "action": "submit_inventory", 
                "year": curr_year,
                "month": f"{curr_month}月",
                "data": data_to_send
            }
            try:
                res = requests.post(GAS_URL, json=payload)
                st.success(f"✅ 盤點存檔成功: {res.text}")
            except Exception as e:
                st.error(f"連線失敗: {e}")

# 功能 3：數據分析看板
elif menu == "3. 數據分析看板":
    st.header("📊 破損統計 Top 5")
    
    # 範例數據 (未來可串接 GAS 抓取當年紀錄檔進行真實分析)
    mock_items = pd.DataFrame({
        "品項": ["陶瓷圓盤", "玻璃杯", "咖啡勺", "紅酒杯", "小味碟"],
        "數量": [15, 12, 8, 5, 4]
    }).sort_values("數量", ascending=True)
    
    mock_reasons = pd.DataFrame({
        "原因": ["洗滌損壞", "客損", "人員疏失", "自然耗損", "其他"],
        "次數": [20, 15, 10, 5, 2]
    })

    col_left, col_right = st.columns(2)
    
    with col_left:
        fig_item = px.bar(
            mock_items, x='數量', y='品項', orientation='h', 
            title="破損品項排名 Top 5", 
            color='數量', color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_item, use_container_width=True)
        
    with col_right:
        fig_reason = px.pie(
            mock_reasons, values='次數', names='原因', 
            title="破損原因分布", hole=0.4
        )
        st.plotly_chart(fig_reason, use_container_width=True)

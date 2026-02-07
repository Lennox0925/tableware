import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

# --- 配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycby5LVZbu19oRUusLZpzXksxMg6ho0T7QhFZvwZ8AIBk4FWckKqyG8tt3JekFQ5Dvvwv-A/exec"

st.set_page_config(layout="wide", page_title="餐具管理系統", page_icon="🍴")

# --- UI 樣式 ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-image: linear-gradient(#2e3131, #1e1e1e); }
    [data-testid="stSidebar"] button { 
        background-color: transparent !important; 
        color: white !important; 
        border: 1px solid #555 !important;
        margin-bottom: 10px;
    }
    [data-testid="stSidebar"] button:hover { border: 1px solid #3498db !important; }
    .stButton>button { width: 100%; height: 60px; font-size: 1.1rem; border-radius: 12px; }
    .stNumberInput input { font-size: 1.8rem !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 初始化 Session ---
if 'menu_option' not in st.session_state: st.session_state.menu_option = "📤 清單管理"
if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
if 'sel_item' not in st.session_state: st.session_state.sel_item = None
if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None

# --- 左框架：純按鈕導覽 ---
with st.sidebar:
    st.title("🍴 餐具管理")
    st.write(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    if st.button("📤 清單管理"): st.session_state.menu_option = "📤 清單管理"
    if st.button("💔 破損登記與同步"): st.session_state.menu_option = "💔 破損登記與同步"
    if st.button("📅 月度盤點結算"): st.session_state.menu_option = "📅 月度盤點結算"
    if st.button("📊 數據看板"): st.session_state.menu_option = "📊 數據看板"
    st.divider()
    if st.button("🚀 立即同步破損紀錄", type="primary"):
        if st.session_state.damage_buffer:
            with st.spinner('同步中...'):
                res = requests.post(GAS_URL, json={"action": "sync_damage", "data": st.session_state.damage_buffer})
                st.success(res.text)
                st.session_state.damage_buffer = []
                st.balloons()
        else: st.warning("目前無暫存資料")

menu = st.session_state.menu_option

# --- 1. 清單管理 ---
if menu == "📤 清單管理":
    st.header("📋 餐具基準清單上傳")
    file = st.file_uploader("選擇 CSV (格式：餐具品項,單位,安全庫存量,店鋪使用量)", type="csv")
    if file:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding='utf-8-sig')
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='big5')
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("💾 確認更新至雲端"):
            with st.spinner('上傳中...'):
                data = [df.columns.tolist()] + df.values.tolist()
                res = requests.post(GAS_URL, json={"action": "update_master_list", "data": data})
                st.success(res.text)

# --- 2. 破損登記 ---
elif menu == "💔 破損登記與同步":
    st.header("💔 破損紀錄 (本機暫存)")
    # 這裡的品項建議手動維持或從 Master 讀取。此處先提供按鈕範例：
    items = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
    reasons = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損"]

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("1. 選擇品項")
        cols = st.columns(4)
        for i, n in enumerate(items):
            if cols[i % 4].button(n, key=f"i_{n}"): st.session_state.sel_item = n
        
        st.subheader("2. 選擇原因")
        cols_r = st.columns(4)
        for i, r in enumerate(reasons):
            if cols_r[i % 4].button(r, key=f"r_{r}"): st.session_state.sel_reason = r
        
        st.info(f"當前選擇：【{st.session_state.sel_item}】 | 【{st.session_state.sel_reason}】")
        qty = st.number_input("3. 輸入數量", min_value=1, step=1, value=None)
        if st.button("➕ 加入暫存清單"):
            if st.session_state.sel_item and st.session_state.sel_reason and qty:
                st.session_state.damage_buffer.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": st.session_state.sel_item, "qty": int(qty), "reason": st.session_state.sel_reason
                })
                st.toast("已加入暫存")
            else: st.warning("請完成選擇與輸入")
    with c2:
        st.subheader("📦 待同步資料")
        if st.session_state.damage_buffer:
            st.dataframe(pd.DataFrame(st.session_state.damage_buffer), use_container_width=True)

# --- 3. 盤點功能 ---
elif menu == "📅 月度盤點結算":
    st.header(f"📅 {datetime.now().month}月度 盤點統計")
    if st.button("🔄 1. 點擊讀取雲端清單並初始化"):
        with st.spinner('讀取中...'):
            res = requests.post(GAS_URL, json={"action": "get_master_list"})
            if res.status_code == 200:
                raw_data = res.json()
                df_init = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                df_init["盤點日期"] = datetime.now().strftime("%Y-%m-%d")
                df_init["進貨數量"] = 0
                df_init["當月盤點總數量"] = 0
                st.session_state.inv_df = df_init
                st.success("清單載入成功！")

    if 'inv_df' in st.session_state:
        st.write("2. 請輸入當月進貨與實盤數量：")
        edited = st.data_editor(
            st.session_state.inv_df,
            column_order=("盤點日期", "餐具品項", "單位", "店鋪使用量", "進貨數量", "當月盤點總數量", "安全庫存量"),
            use_container_width=True, hide_index=True
        )
        if st.button("💾 3. 提交盤點存檔至雲端"):
            with st.spinner('存檔中...'):
                final_data = [edited.columns.tolist()] + edited.fillna(0).values.tolist()
                res = requests.post(GAS_URL, json={"action": "submit_inventory", "data": final_data})
                st.success(res.text)

# --- 4. 看板 ---
elif menu == "📊 數據看板":
    st.header("📊 破損分析 Top 5")
    # 這裡放正確的模擬數據防止 SyntaxError
    df_p = pd.DataFrame({"品項": ["玻璃杯", "陶瓷盤", "咖啡匙"], "數量": [10, 8, 5]})
    df_r = pd.DataFrame({"原因": ["洗滌", "客損", "疏失"], "次數": [12, 7, 4]})
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.bar(df_p, x='數量', y='品項', orientation='h', title="品項排行"), use_container_width=True)
    with c2: st.plotly_chart(px.pie(df_r, values='次數', names='原因', title="原因分布"), use_container_width=True)

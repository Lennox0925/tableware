import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import plotly.express as px

# --- 配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbxTHsogTbjfxkE00sSAEDR7Yn9SdtwId3aH2S2Wf6qsQmXXPxA-IZ09iSqDyGd9j8DC-g/exec"

st.set_page_config(layout="wide", page_title="餐具盤點系統", page_icon="🍴")

# --- UI 樣式修正：左框架改為純按鈕導覽 ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-image: linear-gradient(#2e3131, #1e1e1e); }
    /* 左側選單按鈕樣式 */
    .menu-btn { margin-bottom: 10px; }
    /* 隱藏原生 radio 圓圈 */
    [data-testid="stSidebar"] .stRadio > div { display: none; }
    .stButton>button { width: 100%; height: 60px; font-size: 1.1rem; border-radius: 12px; }
    .stNumberInput input { font-size: 1.8rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 初始化 Session ---
if 'menu_option' not in st.session_state: st.session_state.menu_option = "📤 清單管理"
if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
if 'sel_item' not in st.session_state: st.session_state.sel_item = None
if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None

# --- 左框架：純按鈕導覽 ---
with st.sidebar:
    st.title("🍴 餐具管理系統")
    st.write(f"📅 今日：{datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    
    # 使用按鈕更換選單狀態
    if st.button("📤 清單管理"): st.session_state.menu_option = "📤 清單管理"
    if st.button("💔 破損登記與同步"): st.session_state.menu_option = "💔 破損登記與同步"
    if st.button("📅 月度盤點結算"): st.session_state.menu_option = "📅 月度盤點結算"
    if st.button("📊 數據看板"): st.session_state.menu_option = "📊 數據看板"
    
    st.divider()
    if st.button("🚀 立即同步破損紀錄", type="primary"):
        if st.session_state.damage_buffer:
            with st.spinner('同步中...'):
                res = requests.post(GAS_URL, json={"action": "sync_damage", "data": st.session_state.damage_buffer})
                st.success("同步成功！")
                st.session_state.damage_buffer = []
                st.balloons()
        else: st.warning("無待同步資料")

menu = st.session_state.menu_option

# --- 右框架功能內容 ---

# 1. 清單管理
if menu == "📤 清單管理":
    st.header("📋 餐具清單管理")
    up_file = st.file_uploader("上傳 CSV 基準清單 (餐具品項,單位,安全庫存量,店鋪使用量)", type="csv")
    if up_file:
        try:
            up_file.seek(0)
            df = pd.read_csv(up_file, encoding='utf-8-sig')
        except:
            up_file.seek(0)
            df = pd.read_csv(up_file, encoding='big5')
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("💾 確認更新至雲端"):
            with st.spinner('上傳中...'):
                data = [df.columns.tolist()] + df.values.tolist()
                requests.post(GAS_URL, json={"action": "update_master_list", "data": data})
                st.success("雲端 Master 已更新！")

# 2. 破損紀錄
elif menu == "💔 破損登記與同步":
    st.header("💔 破損登記")
    items = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
    reasons = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損"]

    col_l, col_r = st.columns()
    with col_l:
        st.subheader("1. 選擇品項")
        ci = st.columns(4)
        for i, n in enumerate(items):
            if ci[i % 4].button(n, key=f"i_{n}"): st.session_state.sel_item = n
        
        st.subheader("2. 選擇原因")
        cr = st.columns(4)
        for i, r in enumerate(reasons):
            if cr[i % 4].button(r, key=f"r_{r}"): st.session_state.sel_reason = r
        
        st.info(f"當前：【{st.session_state.sel_item}】 | 【{st.session_state.sel_reason}】")
        qty = st.number_input("3. 輸入數量", min_value=1, step=1, value=None)
        if st.button("➕ 加入暫存"):
            if st.session_state.sel_item and st.session_state.sel_reason and qty:
                st.session_state.damage_buffer.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": st.session_state.sel_item, "qty": int(qty), "reason": st.session_state.sel_reason
                })
                st.toast("已暫存")
            else: st.warning("資訊不完整")

    with col_r:
        st.subheader("📦 待同步清單")
        if st.session_state.damage_buffer:
            st.table(pd.DataFrame(st.session_state.damage_buffer))

# 3. 盤點功能 (從 Master 讀取內容)
elif menu == "📅 月度盤點結算":
    st.header(f"📅 {datetime.now().month}月度 盤點統計")
    
    # 嘗試從 GAS 抓取 Master 清單來初始化表格
    if st.button("🔄 讀取最新餐具清單並初始化盤點表"):
        with st.spinner('讀取雲端清單中...'):
            res = requests.post(GAS_URL, json={"action": "get_master_list"})
            if res.status_code == 200:
                master_data = res.json()
                st.session_state.inv_df = pd.DataFrame(master_data[1:], columns=master_data[0])
                # 增加盤點專用欄位
                st.session_state.inv_df["盤點日期"] = datetime.now().strftime("%Y-%m-%d")
                st.session_state.inv_df["進貨數量"] = 0
                st.session_state.inv_df["當月盤點總數量"] = 0
                st.session_state.inv_df["當月破損量"] = 0 # 提交時再計算
                st.success("清單載入成功！請在下方表格輸入數據。")

    if 'inv_df' in st.session_state:
        # 只允許編輯「進貨數量」與「當月盤點總數量」
        edited_df = st.data_editor(
            st.session_state.inv_df,
            column_order=("盤點日期", "餐具品項", "單位", "店鋪使用量", "進貨數量", "當月盤點總數量", "安全庫存量"),
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("💾 提交盤點存檔至雲端"):
            with st.spinner('正在上傳...'):
                # 這裡可以加入破損量計算邏輯 (選做)
                data = [edited_df.columns.tolist()] + edited_df.fillna(0).values.tolist()
                res = requests.post(GAS_URL, json={"action": "submit_inventory", "data": data})
                st.success(res.text)

# 4. 看板
elif menu == "📊 數據看板":
    st.header("📊 破損分析 Top 5")
    c1, c2 = st.columns(2)
    # 範例圖表
    with c1: st.plotly_chart(px.bar(pd.DataFrame({"項":["A","B","C"],"量":}), x='量', y='項', orientation='h'))
    with c2: st.plotly_chart(px.pie(pd.DataFrame({"原":["X","Y"],"次":}), values='次', names='原'))

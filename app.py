import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

# --- 核心配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbx-P7gv8hpkr67lUxM_NAb24dNnvQMfRqzc4OWZNV60eNLle3MkT-Qug7xyBX6LT2RQGA/exec"

st.set_page_config(layout="wide", page_title="餐具管理系統", page_icon="🍴")

# --- UI 樣式 (左框架導覽按鈕化 & 高對比色) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-image: linear-gradient(#2e3131, #1e1e1e); }
    [data-testid="stSidebar"] button { 
        background-color: transparent !important; color: white !important; 
        border: 1px solid #555 !important; margin-bottom: 10px;
    }
    .stButton>button { width: 100%; height: 60px; font-size: 1.1rem; border-radius: 12px; }
    .stNumberInput input { font-size: 2rem !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 初始化 Session ---
if 'menu_option' not in st.session_state: st.session_state.menu_option = "📤 清單管理"
if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
if 'inv_buffer' not in st.session_state: st.session_state.inv_buffer = []
if 'sel_item' not in st.session_state: st.session_state.sel_item = None
if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None
if 'master_items' not in st.session_state: st.session_state.master_items = []

# --- 左框架：導覽按鈕 ---
with st.sidebar:
    st.title("🍴 餐具管理")
    if st.button("📤 清單管理"): st.session_state.menu_option = "📤 清單管理"
    if st.button("💔 破損登記與同步"): st.session_state.menu_option = "💔 破損登記與同步"
    if st.button("📅 月度盤點結算"): st.session_state.menu_option = "📅 月度盤點結算"
    if st.button("📊 數據看板"): st.session_state.menu_option = "📊 數據看板"
    st.divider()
    st.write(f"📅 {datetime.now().strftime('%Y-%m-%d')}")

menu = st.session_state.menu_option

# --- 1. 清單管理 ---
if menu == "📤 清單管理":
    st.header("📋 餐具基準清單上傳")
    file = st.file_uploader("選擇 CSV (品項,單位,安全庫存量,店鋪使用量)", type="csv")
    if file:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding='utf-8-sig')
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='big5')
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("💾 確認更新至雲端 Master"):
            with st.spinner('上傳中...'):
                data = [df.columns.tolist()] + df.values.tolist()
                res = requests.post(GAS_URL, json={"action": "update_master_list", "data": data})
                st.success(res.text)

# --- 2. 破損登記 ---
elif menu == "💔 破損登記與同步":
    st.header("💔 破損紀錄 (本機暫存)")
    # 此處建議實際由 Master 讀取，範例提供固定品項
    items = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
    reasons = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損"]

    c1, c2 = st.columns()
    with c1:
        st.subheader("1. 選擇品項")
        cols = st.columns(4)
        for i, n in enumerate(items):
            if cols[i % 4].button(n, key=f"i_{n}"): st.session_state.sel_item = n
        st.subheader("2. 選擇原因")
        cols_r = st.columns(4)
        for i, r in enumerate(reasons):
            if cols_r[i % 4].button(r, key=f"r_{r}"): st.session_state.sel_reason = r
        st.info(f"選取：【{st.session_state.sel_item}】 | 【{st.session_state.sel_reason}】")
        qty = st.number_input("3. 輸入破損數", min_value=1, step=1, value=None)
        if st.button("➕ 加入破損暫存"):
            if st.session_state.sel_item and st.session_state.sel_reason and qty:
                st.session_state.damage_buffer.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": st.session_state.sel_item, "qty": int(qty), "reason": st.session_state.sel_reason})
                st.toast("破損已暫存")
            else: st.warning("請完整選擇")
    with c2:
        st.subheader("📦 待同步資料")
        st.dataframe(pd.DataFrame(st.session_state.damage_buffer), use_container_width=True)
        if st.button("🚀 同步破損紀錄至雲端"):
            with st.spinner('同步中...'):
                requests.post(GAS_URL, json={"action": "sync_damage", "data": st.session_state.damage_buffer})
                st.session_state.damage_buffer = []
                st.success("同步成功")

# --- 3. 盤點功能 (暫存 + 統一整合上傳) ---
elif menu == "📅 月度盤點結算":
    st.header(f"📅 {datetime.now().month}月 盤點結算")
    
    if st.button("🔄 讀取雲端清單基準"):
        with st.spinner('連線中...'):
            res = requests.post(GAS_URL, json={"action": "get_master_list"})
            raw = res.json()
            st.session_state.master_df = pd.DataFrame(raw[1:], columns=raw[0])
            st.session_state.master_items = st.session_state.master_df['餐具品項'].tolist()
            st.success("清單讀取成功！")

    if st.session_state.master_items:
        c1, c2 = st.columns()
        with c1:
            st.subheader("1. 選擇盤點品項")
            cols = st.columns(4)
            for i, n in enumerate(st.session_state.master_items):
                if cols[i % 4].button(n, key=f"inv_{n}"): st.session_state.sel_inv_item = n
            
            st.info(f"正在盤點：【{st.session_state.get('sel_inv_item', '未選擇')}】")
            inv_qty = st.number_input("2. 輸入實盤總數量", min_value=0, step=1, value=None)
            in_qty = st.number_input("3. 輸入本月進貨數", min_value=0, step=1, value=None)
            
            if st.button("➕ 加入盤點暫存"):
                if st.session_state.get('sel_inv_item') and inv_qty is not None:
                    st.session_state.inv_buffer.append({
                        "餐具品項": st.session_state.sel_inv_item,
                        "當月盤點總數量": int(inv_qty),
                        "進貨數量": int(in_qty if in_qty else 0)
                    })
                    st.toast(f"{st.session_state.sel_inv_item} 已加入暫存")
                else: st.warning("請選擇品項並輸入數量")

        with c2:
            st.subheader("📦 盤點暫存清單")
            if st.session_state.inv_buffer:
                temp_inv_df = pd.DataFrame(st.session_state.inv_buffer)
                # 整合相同品項 (取最後一筆輸入)
                final_inv = temp_inv_df.groupby("餐具品項").last().reset_index()
                st.dataframe(final_inv, use_container_width=True)
                
                if st.button("🚀 整合並提交月報表", type="primary"):
                    with st.spinner('整合數據中...'):
                        # 合併 Master 清單與盤點數據
                        report = st.session_state.master_df.merge(final_inv, on="餐具品項", how="left").fillna(0)
                        report["盤點日期"] = datetime.now().strftime("%Y-%m-%d")
                        # 自動計算破損量
                        # 假設破損量計算 = (店鋪使用量 + 進貨) - 當月盤點 [此邏輯可視需求調整]
                        report["當月破損量"] = (report["店鋪使用量"].astype(int) + report["進貨數量"].astype(int)) - report["當月盤點總數量"].astype(int)
                        
                        data_to_send = [report.columns.tolist()] + report.values.tolist()
                        res = requests.post(GAS_URL, json={"action": "submit_inventory", "data": data_to_send})
                        st.success(res.text)
                        st.session_state.inv_buffer = []

# --- 4. 看板 ---
elif menu == "📊 數據看板":
    st.header("📊 破損分析 Top 5")
    df_p = pd.DataFrame({"品項": ["玻璃杯", "陶瓷盤", "咖啡匙"], "數量": [12, 8, 5]})
    df_r = pd.DataFrame({"原因": ["洗滌", "客損", "疏失"], "次數": [10, 5, 2]})
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.bar(df_p, x='數量', y='品項', orientation='h', title="品項排行"))
    with c2: st.plotly_chart(px.pie(df_r, values='次數', names='原因', title="原因分布"))

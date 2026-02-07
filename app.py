import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

# --- 配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwo4i3uGFRIiWX26Idi3W4DTW8YAnJP-3uFND-wAiTfBuSHEiyG5imHcDUmCn90msJqyA/exec"

st.set_page_config(layout="wide", page_title="餐具盤點系統")

# --- UI 修正 ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e1e1e !important; color: white !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { width: 100%; height: 60px; font-size: 1.1rem; border-radius: 10px; margin-bottom: 5px; }
    .stNumberInput input { font-size: 2rem !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 初始化 Session ---
if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
if 'sel_item' not in st.session_state: st.session_state.sel_item = None
if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None

# --- 左框架 ---
with st.sidebar:
    st.title("🍴 餐具管理系統")
    menu = st.radio("功能導覽", ["1. 餐具清單上下載", "2. 餐具破損登記", "3. 餐具盤點統計", "4. 數據分析看板"])
    st.divider()
    if st.button("🚀 同步破損紀錄至雲端"):
        if st.session_state.damage_buffer:
            res = requests.post(GAS_URL, json={"action": "sync_damage", "data": st.session_state.damage_buffer})
            st.success(res.text)
            st.session_state.damage_buffer = []
        else: st.warning("無暫存資料")

# --- 右框架內容 ---

# 1. 餐具清單 (Master)
if menu == "1. 餐具清單上下載":
    st.header("📋 清單管理與初始化")
    up_file = st.file_uploader("上傳 CSV 清單 (品項, 單位, 安全庫存, 使用量)", type="csv")
    if up_file:
        try:
            up_file.seek(0)
            df = pd.read_csv(up_file, encoding='utf-8-sig')
        except:
            up_file.seek(0)
            df = pd.read_csv(up_file, encoding='big5')
        st.dataframe(df, use_container_width=True)
        if st.button("💾 更新 Master 清單至雲端"):
            data = [df.columns.tolist()] + df.values.tolist()
            requests.post(GAS_URL, json={"action": "update_master_list", "data": data})
            st.success("Master 已更新")

# 2. 破損登記 (按鈕操作)
elif menu == "2. 餐具破損登記":
    st.header("💔 破損登記 (本機暫存)")
    # 此處建議實際從 Master 檔抓取，範例使用靜態
    items = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
    reasons = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損"]

    st.subheader("第一步：選擇品項")
    c_i = st.columns(4)
    for idx, n in enumerate(items):
        if c_i[idx % 4].button(n, key=f"i_{n}"): st.session_state.sel_item = n

    st.subheader("第二步：選擇原因")
    c_r = st.columns(4)
    for idx, r in enumerate(reasons):
        if c_r[idx % 4].button(r, key=f"r_{r}"): st.session_state.sel_reason = r

    st.info(f"當前選擇：品項【{st.session_state.sel_item}】 | 原因【{st.session_state.sel_reason}】")
    
    qty = st.number_input("第三步：輸入數量", min_value=1, step=1, value=None)

    if st.button("➕ 加入暫存", type="primary"):
        if st.session_state.sel_item and st.session_state.sel_reason and qty:
            st.session_state.damage_buffer.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "item": st.session_state.sel_item,
                "qty": int(qty),
                "reason": st.session_state.sel_reason
            })
            st.success("已暫存，請記得最後點擊左側「同步」按鈕上傳。")
            st.session_state.sel_item = st.session_state.sel_reason = None
        else: st.warning("請填寫完整資訊")

    if st.session_state.damage_buffer:
        st.write("待同步清單：", pd.DataFrame(st.session_state.damage_buffer))

# 3. 盤點功能 (提交到專屬盤點檔案)
elif menu == "3. 餐具盤點統計":
    st.header(f"📅 {datetime.now().month}月度 盤點結算")
    st.write("請輸入當月數據，系統將自動存入該年度的「餐具盤點檔案」中。")
    
    # 建構表格欄位
    inv_df = pd.DataFrame({
        "盤點日期": [datetime.now().strftime("%Y-%m-%d")],
        "餐具品項": [""],
        "當月破損量": [0], # 公式計算點
        "盤點總數量": [None],
        "店鋪使用量": [None],
        "進貨數量": [None],
        "安全庫存量": [None]
    })
    
    st.write("💡 提示：當月破損量 = (上月盤點總量 + 進貨數量) - 當月盤點總量")
    edited = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 提交盤點資料至雲端檔"):
        month_str = f"{datetime.now().month}月"
        data = [edited.columns.tolist()] + edited.fillna("").values.tolist()
        res = requests.post(GAS_URL, json={"action": "submit_inventory", "month": month_str, "data": data})
        st.success(res.text)

# 4. 數據分析
elif menu == "4. 數據分析看板":
    st.header("📊 破損分析 Top 5")
    # 範例數據
    df_p = pd.DataFrame({"品項": ["玻璃杯", "平盤", "味碟", "咖啡杯", "碗"], "數量": [15, 12, 10, 8, 5]})
    df_r = pd.DataFrame({"原因": ["洗滌", "客損", "疏失", "耗損"], "次數": [20, 15, 10, 5]})
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.bar(df_p, x='數量', y='品項', orientation='h', title="品項排行"), use_container_width=True)
    with c2: st.plotly_chart(px.pie(df_r, values='次數', names='原因', title="原因分布"), use_container_width=True)

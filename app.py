import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import plotly.express as px

# --- 配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbxTHsogTbjfxkE00sSAEDR7Yn9SdtwId3aH2S2Wf6qsQmXXPxA-IZ09iSqDyGd9j8DC-g/exec"

st.set_page_config(layout="wide", page_title="餐具盤點系統", page_icon="🍴")

# --- UI 樣式修正：恢復美觀左框架 ---
st.markdown("""
    <style>
    /* 側邊欄背景與文字顏色 */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#2e3131, #1e1e1e);
        color: white !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #ecf0f1 !important;
        font-weight: 500;
    }
    /* 按鈕美化 */
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 1.1rem;
        border-radius: 12px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        border: 2px solid #3498db;
        color: #3498db;
    }
    /* 數字輸入框加大 */
    .stNumberInput input { font-size: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 初始化 ---
if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
if 'sel_item' not in st.session_state: st.session_state.sel_item = None
if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None

# --- 左框架：導覽列 ---
with st.sidebar:
    st.title("🍴 餐具管理系統")
    st.write(f"📅 系統日期：{datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    menu = st.radio("功能切換", ["📤 清單管理", "💔 破損紀錄與同步", "📅 月度盤點結算", "📊 數據看板"])
    st.divider()
    st.caption("版本 v1.5 | 平板專用介面")

# --- 右框架內容 ---

# 1. 清單管理
if menu == "📤 清單管理":
    st.header("📋 餐具清單管理")
    col_up, col_down = st.columns(2)
    with col_up:
        up_file = st.file_uploader("上傳 CSV 基準清單", type="csv")
        if up_file:
            try:
                up_file.seek(0)
                df = pd.read_csv(up_file, encoding='utf-8-sig')
            except:
                up_file.seek(0)
                df = pd.read_csv(up_file, encoding='big5')
            st.dataframe(df, use_container_width=True)
            if st.button("💾 確認更新至雲端"):
                with st.spinner('正在同步清單...'):
                    data = [df.columns.tolist()] + df.values.tolist()
                    requests.post(GAS_URL, json={"action": "update_master_list", "data": data})
                    st.success("Master 清單更新成功！")

# 2. 破損紀錄與同步 (整合成同一頁)
elif menu == "💔 破損紀錄與同步":
    st.header("💔 破損登記與雲端同步")
    
    # 按鈕矩陣配置 (4xN)
    items = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
    reasons = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損"]

    col_input, col_sync = st.columns([2, 1], gap="large")

    with col_input:
        st.subheader("1. 選擇品項")
        ci = st.columns(4)
        for i, n in enumerate(items):
            if ci[i % 4].button(n, key=f"i_{n}"): st.session_state.sel_item = n

        st.subheader("2. 選擇原因")
        cr = st.columns(4)
        for i, r in enumerate(reasons):
            if cr[i % 4].button(r, key=f"r_{r}"): st.session_state.sel_reason = r
        
        st.info(f"👉 目前選取：【{st.session_state.sel_item}】 + 【{st.session_state.sel_reason}】")
        qty = st.number_input("3. 輸入數量 (整數)", min_value=1, step=1, value=None)

        if st.button("➕ 加入暫存", type="primary"):
            if st.session_state.sel_item and st.session_state.sel_reason and qty:
                st.session_state.damage_buffer.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": st.session_state.sel_item,
                    "qty": int(qty),
                    "reason": st.session_state.sel_reason
                })
                st.toast("已加入暫存！")
            else: st.warning("請完整選擇品項、原因與數量")

    with col_sync:
        st.subheader("📦 本機暫存區")
        if st.session_state.damage_buffer:
            tmp_df = pd.DataFrame(st.session_state.damage_buffer)
            st.dataframe(tmp_df, use_container_width=True)
            
            if st.button("🚀 同步至雲端紀錄檔"):
                with st.spinner('正在同步至雲端資料夾...'):
                    res = requests.post(GAS_URL, json={"action": "sync_damage", "data": st.session_state.damage_buffer})
                    time.sleep(1) # 動態效果感
                    st.success(res.text)
                    st.session_state.damage_buffer = [] # 清空
                    st.balloons() # 成功動畫
            
            # 提供本地下載備份
            st.download_button("📥 下載暫存檔 (CSV)", tmp_df.to_csv(index=False), "backup.csv")
        else:
            st.write("目前沒有待同步的資料。")

# 3. 盤點統計
elif menu == "📅 月度盤點結算":
    st.header(f"📅 {datetime.now().month}月 盤點結算")
    st.write("請編輯下方表格，完成後提交至年度盤點檔。")
    
    inv_df = pd.DataFrame({
        "盤點日期": [datetime.now().strftime("%Y-%m-%d")],
        "餐具品項": [""],
        "當月破損量": [None],
        "盤點總數量": [None],
        "店鋪使用量": [None],
        "進貨數量": [None],
        "安全庫存量": [None]
    })
    
    edited = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 提交當月盤點至雲端"):
        with st.spinner('正在計算並存檔...'):
            data = [edited.columns.tolist()] + edited.fillna("").values.tolist()
            res = requests.post(GAS_URL, json={"action": "submit_inventory", "data": data})
            st.success(res.text)

# 4. 分析看板
elif menu == "📊 數據看板":
    st.header("📊 當年破損分析 (Top 5)")
    df_p = pd.DataFrame({"品項": ["玻璃杯", "平盤", "味碟", "咖啡杯", "碗"], "數量": [15, 12, 10, 8, 5]})
    df_r = pd.DataFrame({"原因": ["洗滌", "客損", "疏失", "耗損"], "次數": [20, 10, 5, 5]})
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.bar(df_p, x='數量', y='品項', orientation='h', title="品項排行"), use_container_width=True)
    with c2: st.plotly_chart(px.pie(df_r, values='次數', names='原因', title="原因分布"), use_container_width=True)

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import plotly.express as px

# --- 核心配置 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbxhvUl-BHXp3daZzbEVp3k27QBBfqU_qy_W3QNwtXBuPdeYHnuknBZKedEw486hrcPUbg/exec"

st.set_page_config(layout="wide", page_title="餐具雲端盤點系統", page_icon="🍴")

# --- 平板介面 CSS 優化 ---
st.markdown("""
    <style>
    /* 左側選單顏色修正 */
    [data-testid="stSidebar"] {
        background-color: #262730 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {
        color: #FFFFFF !important;
    }
    /* 按鈕樣式 */
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 1.1rem;
        border-radius: 10px;
        font-weight: bold;
    }
    /* 選中狀態的按鈕模擬樣式可透過顏色區分 (這裡使用 st.columns 建立矩陣) */
    .stNumberInput input { font-size: 1.8rem !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 側邊欄：左框架 ---
with st.sidebar:
    st.title("🍴 餐具管理系統")
    st.write(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()
    
    # 功能導覽
    menu = st.radio("功能導覽", ["1. 清單初始化", "2. 破損/盤點登記", "3. 數據分析看板"])
    
    st.divider()
    if st.button("🚀 同步暫存至雲端"):
        if 'damage_buffer' in st.session_state and st.session_state.damage_buffer:
            try:
                payload = {"action": "sync_damage", "data": st.session_state.damage_buffer}
                res = requests.post(GAS_URL, json=payload)
                if res.status_code == 200:
                    st.success("同步成功！")
                    st.session_state.damage_buffer = []
                    st.rerun()
            except Exception as e:
                st.error(f"錯誤: {e}")
        else:
            st.info("無待同步資料")

# --- 右框架內容 ---

if menu == "1. 清單初始化":
    st.header("📋 上傳餐具清單")
    file = st.file_uploader("選擇 CSV 檔案", type="csv")
    if file:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding='utf-8-sig')
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='big5')
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("💾 確認上傳至雲端"):
            data_list = [df.columns.tolist()] + df.values.tolist()
            requests.post(GAS_URL, json={"action": "update_master_list", "data": data_list})
            st.success("雲端 Master 已更新")

elif menu == "2. 破損/盤點登記":
    st.header("📝 紀錄登記")
    
    tab1, tab2 = st.tabs(["破損登記 (按鈕操作)", "月度盤點提交"])
    
    with tab1:
        # --- 破損登記按鈕化 ---
        # 定義品項 (實務上可從 Master List 讀取，這裡示範矩陣)
        item_list = ["陶瓷平盤", "玻璃杯", "咖啡杯", "小碟子", "紅酒杯", "湯匙", "餐叉", "拉麵碗"]
        reason_list = ["洗滌損壞", "人員疏失", "客人打破", "自然耗損", "其他原因"]

        if 'sel_item' not in st.session_state: st.session_state.sel_item = None
        if 'sel_reason' not in st.session_state: st.session_state.sel_reason = None

        st.subheader("1. 選擇品項")
        cols = st.columns(4) # 每列四個按鈕
        for i, name in enumerate(item_list):
            if cols[i % 4].button(name, key=f"btn_{name}"):
                st.session_state.sel_item = name

        st.subheader("2. 選擇原因")
        cols_r = st.columns(4)
        for i, rsn in enumerate(reason_list):
            if cols_r[i % 4].button(rsn, key=f"rsn_{rsn}"):
                st.session_state.sel_reason = rsn

        # 顯示目前選擇
        st.info(f"當前選擇：【{st.session_state.sel_item}】 | 原因：【{st.session_state.sel_reason}】")
        
        d_qty = st.number_input("3. 輸入數量 (整數)", min_value=1, step=1, value=None)

        if st.button("➕ 新增至暫存紀錄", type="primary"):
            if st.session_state.sel_item and st.session_state.sel_reason and d_qty:
                if 'damage_buffer' not in st.session_state: st.session_state.damage_buffer = []
                st.session_state.damage_buffer.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": st.session_state.sel_item,
                    "qty": int(d_qty),
                    "reason": st.session_state.sel_reason
                })
                st.success("已暫存！")
                st.session_state.sel_item = None # 重置
                st.session_state.sel_reason = None
            else:
                st.warning("請確保 品項、原因、數量 皆已選擇/輸入")

        if 'damage_buffer' in st.session_state and st.session_state.damage_buffer:
            st.write("---")
            st.write("📍 待同步清單：")
            st.table(pd.DataFrame(st.session_state.damage_buffer))

    with tab2:
        st.subheader("📅 月度盤點統計")
        # 盤點表格
        inv_df = pd.DataFrame({
            "日期": [datetime.now().strftime("%Y-%m-%d")],
            "品項": [""],
            "盤點數量": [None],
            "進貨數量": [None],
            "店鋪使用量": [None]
        })
        edited = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 提交盤點存檔"):
            data = [edited.columns.tolist()] + edited.values.tolist()
            requests.post(GAS_URL, json={"action": "submit_inventory", "data": data})
            st.success("盤點已存入雲端年度檔案")

elif menu == "3. 數據分析看板":
    st.header("📊 破損 Top 5 圖表")
    # 範例資料
    df_p = pd.DataFrame({"品項": ["玻璃杯", "平盤", "味碟", "咖啡杯", "碗"], "數量": [15, 12, 8, 5, 3]})
    df_r = pd.DataFrame({"原因": ["洗滌", "客損", "疏失", "耗損"], "次數": [20, 10, 5, 2]})

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.bar(df_p, x='數量', y='品項', orientation='h', title="品項排行"), use_container_width=True)
    with c2:
        st.plotly_chart(px.pie(df_r, values='次數', names='原因', title="原因分布"), use_container_width=True)

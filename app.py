import streamlit as st
import pandas as pd
import json
import os
import requests

# -----------------------------
# 数据加载 + 列标准化
# -----------------------------
def standardize_columns(df, cfg):
    # 列名统一小写
    df.columns = [c.lower() for c in df.columns]

    # 按优先级重排
    col_order = []
    for c in ["en", "zh", "notes", "key"]:
        if c in df.columns:
            col_order.append(c)
    others = [c for c in df.columns if c not in col_order]
    df = df[col_order + others]

    # 插入 game_name
    df.insert(0, "game", cfg["game_name"])

    # 插入 game_type（list 转为字符串）
    game_type_str = ", ".join(cfg.get("game_type", []))
    df.insert(1, "game_type", game_type_str)

    return df

def load_data(cfg):
    source_type = cfg.get("source_type")
    path = cfg.get("path")

    try:
        if source_type == "xlsx":
            df = pd.read_excel(path)
        elif source_type == "csv":
            df = pd.read_csv(path)
        elif source_type == "json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        elif source_type == "api":
            data = requests.get(path).json()
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        data = v
                        break
            df = pd.DataFrame(data)
        else:
            st.error(f"未知的数据类型: {source_type}")
            return None

        return standardize_columns(df, cfg)

    except Exception as e:
        st.error(f"读取数据失败: {e}")
        return None

# -----------------------------
# 主程序
# -----------------------------
st.set_page_config(page_title="Game Localization Search", layout="wide")
st.title("🎮 游戏本地化对照查询")

# 加载 config.json
if not os.path.exists("config.json"):
    st.error("⚠️ 没有找到 config.json，请先上传配置文件")
    st.stop()

with open("config.json", "r", encoding="utf-8") as f:
    configs = json.load(f)

# 读取所有游戏数据
all_dfs = []
for cfg in configs:
    df = load_data(cfg)
    if df is not None:
        all_dfs.append(df)

if not all_dfs:
    st.error("⚠️ 没有成功加载任何数据")
    st.stop()

# 合并成全局数据表
global_df = pd.concat(all_dfs, ignore_index=True)

# -----------------------------
# 筛选器
# -----------------------------
search_scope = st.sidebar.radio("选择搜索范围", ["全局", "单个游戏"])
if search_scope == "单个游戏":
    game_choice = st.sidebar.selectbox("选择游戏", global_df["game"].unique())
    search_df = global_df[global_df["game"] == game_choice]
else:
    search_df = global_df

# 游戏类型筛选
all_types = sorted({t for ts in global_df["game_type"].unique() for t in ts.split(", ") if t})
selected_types = st.sidebar.multiselect("筛选游戏类型", all_types)
if selected_types:
    mask = search_df["game_type"].apply(lambda x: any(t in x for t in selected_types))
    search_df = search_df[mask]

# 搜索字段
search_field = st.sidebar.radio("选择搜索字段", ["全部", "中文(zh)", "英文(en)"])
query = st.text_input("输入关键字搜索")

# -----------------------------
# 搜索执行
# -----------------------------
if query:
    if search_field == "全部":
        mask = search_df.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False), axis=1).any(axis=1)
    elif search_field == "中文(zh)" and "zh" in search_df.columns:
        mask = search_df["zh"].astype(str).str.contains(query, case=False, na=False)
    elif search_field == "英文(en)" and "en" in search_df.columns:
        mask = search_df["en"].astype(str).str.contains(query, case=False, na=False)
    else:
        mask = pd.Series([False] * len(search_df))

    results = search_df[mask]
    st.write(f"🔍 搜索结果（共 {len(results)} 条）")
    st.dataframe(results)
else:
    st.write("📋 数据示例")
    st.dataframe(search_df.head(20))
import streamlit as st
import requests
import json
from openai import OpenAI

# 页面配置
st.set_page_config(page_title="PM求职情报精炼机", layout="wide")
st.title("🚀 PM求职情报精炼机")
st.caption("粘贴小红书内容，自动同步至飞书多维表格卡片视图")

# 从 Streamlit Secrets 获取配置（下一步会教你配置）
FEISHU_APP_ID = st.secrets["FEISHU_APP_ID"]
FEISHU_APP_SECRET = st.secrets["FEISHU_APP_SECRET"]
FEISHU_APP_TOKEN = st.secrets["FEISHU_APP_TOKEN"]
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

# 获取飞书 Access Token
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    r = requests.post(url, json=payload)
    return r.json().get("app_access_token")

# 获取飞书表格 ID (自动匹配名为"求职库"的表)
def get_table_id(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    tables = r.json().get("data", {}).get("items", [])
    for t in tables:
        if t['name'] == "求职库":
            return t['table_id']
    return tables[0]['table_id'] if tables else None

# DeepSeek 核心分析逻辑
def analyze_content(title, content, comments):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    prompt = f"""
    你是一位资深产品经理面试官和职业导师。请分析以下小红书求职贴内容。
    
    标题：{title}
    正文：{content}
    精选评论：{comments}
    
    请输出以下三个部分，要求专业、刻薄但实用：
    1. 【简历/项目拆解】：提取项目核心逻辑，指出其写法亮点或改进点。
    2. 【面经分析】：如果是面试贴，提取考察知识点、面试官意图及高分思路。
    3. 【能力补齐建议】：针对该岗位，我（读者）可以从哪个具体动作进行复现或提升。
    
    注意：请直接输出内容，不要带“好的，我明白了”之类的废话。
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content

# 侧边栏输入
with st.sidebar:
    st.header("1. 输入内容")
    post_title = st.text_input("帖子简短标题")
    post_tags = st.multiselect("岗位标签", ["产品经理", "AI产品", "B端产品", "数据产品", "实习", "校招", "社招"])
    post_url = st.text_input("原贴链接")

# 主界面输入
col1, col2 = st.columns(2)
with col1:
    post_content = st.text_area("2. 粘贴帖子正文", height=300)
with col2:
    post_comments = st.text_area("3. 粘贴精选评论", height=300)

if st.button("✨ 开始分析并同步至飞书"):
    if not post_content:
        st.error("请输入正文内容")
    else:
        with st.spinner("AI 正在深度思考并同步中..."):
            try:
                # 1. AI 分析
                analysis_result = analyze_content(post_title, post_content, post_comments)
                
                # 2. 写入飞书
                token = get_feishu_token()
                table_id = get_table_id(token)
                
                fs_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # 简单的文本切分处理（示例）
                parts = analysis_result.split('\n\n')
                res_resume = parts[0] if len(parts) > 0 else ""
                res_interview = parts[1] if len(parts) > 1 else ""
                res_gap = parts[2] if len(parts) > 2 else ""

                data = {
                    "fields": {
                        "帖子标题": post_title,
                        "岗位标签": post_tags,
                        "原始正文": post_content,
                        "精选评论": post_comments,
                        "AI-简历/项目拆解": res_resume,
                        "AI-面经分析": res_interview,
                        "AI-能力补齐建议": res_gap,
                        "原贴链接": {"link": post_url, "text": "点击查看原贴"} if post_url else None
                    }
                }
                
                r = requests.post(fs_url, headers=headers, json=data)
                
                if r.status_code == 200:
                    st.success("🎉 同步成功！快去飞书多维表格查看你的精美卡片吧！")
                    st.markdown("### AI 分析预览")
                    st.write(analysis_result)
                else:
                    st.error(f"同步失败: {r.json().get('msg')}")
            except Exception as e:
                st.error(f"发生错误: {str(e)}")

import streamlit as st
import requests
from openai import OpenAI

# 页面配置
st.set_page_config(page_title="PM求职情报精炼机", layout="wide")
st.title("🚀 PM求职情报精炼机 (全兼容版)")

# 从 Secrets 获取配置
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

# DeepSeek 分析
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
    # 为了防止多选类型不匹配，这里直接改用逗号分隔的文本输入
    post_tags = st.text_input("岗位标签 (如: 产品经理, 实习)")
    post_url = st.text_input("原帖链接")

# 主界面输入
col1, col2 = st.columns(2)
with col1:
    post_content = st.text_area("2. 粘贴帖子正文", height=200)
with col2:
    post_comments = st.text_area("3. 粘贴精选评论", height=200)

if st.button("✨ 开始分析并同步至飞书"):
    if not post_content:
        st.error("请输入正文内容")
    else:
        with st.spinner("AI 分析中并尝试写入..."):
            try:
                token = get_feishu_token()
                table_id = "tblXQp5ehczgYOJZ" 
                
                # 1. AI 分析
                analysis_result = analyze_content(post_title, post_content, post_comments)
                
                # 2. 写入飞书
                fs_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # 结果拆分
                parts = analysis_result.split('【')
                res_resume = "【" + parts[1] if len(parts) > 1 else analysis_result
                res_interview = "【" + parts[2] if len(parts) > 2 else ""
                res_gap = "【" + parts[3] if len(parts) > 3 else ""

                # 【重要修正】：所有字段全部发送纯字符串，确保兼容飞书的“文本”列
                data = {
                    "fields": {
                        "帖子标题": str(post_title),
                        "岗位标签": str(post_tags),
                        "原始正文": str(post_content),
                        "精选评论": str(post_comments),
                        "AI-简历/项目拆解": str(res_resume),
                        "AI-面经分析": str(res_interview),
                        "AI-能力补齐建议": str(res_gap),
                        "原帖链接": str(post_url) # 这里不再发字典，直接发链接文本
                    }
                }
                
                r = requests.post(fs_url, headers=headers, json=data)
                resp_json = r.json()
                
                if r.status_code == 200 and resp_json.get("code") == 0:
                    st.success("🎉 终于成功了！数据已同步到飞书。")
                    st.markdown("### AI 分析预览")
                    st.write(analysis_result)
                else:
                    st.error("同步失败！")
                    st.json(resp_json)
            except Exception as e:
                st.error(f"程序错误: {str(e)}")

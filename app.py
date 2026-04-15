import streamlit as st
import requests
from openai import OpenAI

# 页面配置
st.set_page_config(page_title="PM求职情报精炼机", layout="wide")
st.title("🚀 PM求职情报精炼机 (精准修正版)")

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

# DeepSeek 核心分析逻辑
def analyze_content(title, content, comments):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    prompt = f"你是一位资深PM面试官。请分析：标题：{title}\n正文：{content}\n评论：{comments}\n输出：【分析1】、【分析2】、【分析3】。不要废话。"
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
    # 强制将标签转为字符串，防止飞书类型匹配错误
    post_tags = st.text_input("岗位标签 (多个用逗号隔开)", "产品经理")
    post_url = st.text_input("原贴链接")

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
                # 1. AI 分析
                analysis_result = analyze_content(post_title, post_content, post_comments)
                
                # 2. 准备写入飞书
                token = get_feishu_token()
                # 【关键修正】：这里直接填入你截图里的 Table ID，不再动态获取
                table_id = "tblXQp5ehczgYOJZ" 
                
                fs_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # AI 结果简单拆分
                parts = analysis_result.split('【')
                res_resume = "【" + parts[1] if len(parts) > 1 else analysis_result
                res_interview = "【" + parts[2] if len(parts) > 2 else ""
                res_gap = "【" + parts[3] if len(parts) > 3 else ""

                data = {
                    "fields": {
                        "帖子标题": post_title,
                        "岗位标签": post_tags, # 现在是文本格式，更稳
                        "原始正文": post_content,
                        "精选评论": post_comments,
                        "AI-简历/项目拆解": res_resume,
                        "AI-面经分析": res_interview,
                        "AI-能力补齐建议": res_gap,
                        "原贴链接": {"link": post_url, "text": "点击查看原贴"} if post_url else None
                    }
                }
                
                r = requests.post(fs_url, headers=headers, json=data)
                resp_json = r.json()
                
                if r.status_code == 200 and resp_json.get("code") == 0:
                    st.success("🎉 写入成功！请刷新飞书页面查看。")
                    st.markdown("### AI 分析预览")
                    st.write(analysis_result)
                else:
                    st.error(f"飞书拒绝了写入请求！错误信息：{resp_json.get('msg')}")
                    st.json(resp_json) # 显示完整的错误报告
            except Exception as e:
                st.error(f"发生程序错误: {str(e)}")

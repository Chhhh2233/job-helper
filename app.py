import streamlit as st
import requests
from openai import OpenAI
import re

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
    标题：{title}
    正文：{content}
    精选评论：{comments}
    
    # Role
    你是一位拥有10年以上经验的“全能型互联网专家”，曾担任大厂高级HR、核心业务主管、技术架构师及资深产品经理。你擅长从细微的面试问题中洞察业务本质，并将高深的商业逻辑转化为易懂的实操指南。
    
    # Context
    我是一名工科硕士生，虽然逻辑性强但缺乏实习经验，技术背景偏弱。我希望通过“拆解他人面经”的方式，学习真实的业务思维、商务逻辑以及实际工作中的标准作业程序（SOP）。
    
    # Task
    请针对我提供的[面经内容]，完成以下深度拆解：
    ## 1. 问题多维分类与意图洞察
    请将面经中的问题分类（如：业务执行、数据决策、商业洞察、团队协作等）。
    - 要求：用表格形式呈现。
    - 必须包含“考察本质”列：用一句话说明面试官问这个问题，背后是在担心什么或想确认什么能力。
    
    ## 2. 核心题型回答策略（带“大白话”翻译）
    请针对每一类问题提供通用的回答逻辑（框架）。
    - 要求：提供一个“工科生友好”的思维模型（如：输入-逻辑-输出）。
    - 必须包含【大白话补丁】：解释其中的行内话或专业术语，确保没有任何工作经验的人也能听懂。
    
    ## 3. 业务逆向工程：岗位日常与SOP推导
    这是我最看重的部分。请根据面经问题，反向推导出这个岗位在真实工作中是如何运转的。
    - 请梳理出 3-4 个核心工作流程（如：需求评审、灰度测试、竞品调研等）。
    - 要求：以 SOP（步骤 1, 2, 3...）的形式展现。
    
    ## 4. 给“零经验工科生”的降维打击建议
    基于这段面经，我作为一个工科生，在没有实习的情况下，可以用哪些“硬核思维”或“逻辑工具”来平替那些缺失的业务经验？
    # Constraints
    - 语言风格：专业且务实，像是一位良师益友在带徒弟。
    - 严禁生编乱造：如果面经信息不足，基于大厂共性逻辑进行合理推演，并注明“行业通案”。
    - 易懂性：所有专业术语（如：A/B Test, 留存, 转化, 北极星指标）必须在初次出现时附带大白话解释。
    -请直接输出内容，不要带“好的，我明白了”之类的废话。
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
                
                # 结果拆分 (适配新版 Prompt 的 ## 1, 2, 3, 4 结构)
                # 使用正则表达式切分，兼容 "## 1." 或 "## 1、" 等大模型常见的轻微符号变体
                pattern = r'(?:^|\n)##\s*[1-4][.、]'
                parts = re.split(pattern, analysis_result)
                
                # 正常情况下，parts 长度至少为 5 (parts[0]是前言或空，1~4分别对应四个模块)
                if len(parts) >= 5:
                    # 将模块1(意图)和模块2(策略)合并放入面经分析列
                    res_interview = "## 1." + parts[1].strip() + "\n\n## 2." + parts[2].strip()
                    # 将模块3(SOP推导)放入简历/项目拆解列
                    res_resume = "## 3." + parts[3].strip()
                    # 将模块4(降维打击建议)放入能力补齐列
                    res_gap = "## 4." + parts[4].strip()
                else:
                    # 防呆/保底机制：如果大模型偶发性没有按 1/2/3/4 格式输出
                    res_interview = analysis_result
                    res_resume = "⚠️ 内容排版变动，请在【AI-面经分析】列查看完整提取结果。"
                    res_gap = "⚠️ 内容排版变动，请在【AI-面经分析】列查看完整提取结果。"

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

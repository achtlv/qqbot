import os
import time
import threading
import uvicorn
import botpy
from botpy.message import C2CMessage, GroupMessage
from openai import OpenAI
from fastapi import FastAPI

# ================= 配置区域 =================
API_KEY = os.environ.get("OPENAI_API_KEY")
# 建议在 Render 环境变量中，将 BASE_URL 设置为国际版 https://api.z.ai/api/paas/v4
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
MODEL_NAME = os.environ.get("MODEL_NAME", "glm-4.7-flash")
QQ_APP_ID = os.environ.get("QQ_APP_ID")
QQ_APP_SECRET = os.environ.get("QQ_APP_SECRET")

# 群聊触发前缀
TRIGGER_PREFIX = ".ai"

# 增加超时时间到 60 秒
ai = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60.0, max_retries=0)

# ================= Web 健康检查服务 =================
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================= 通用 AI 请求函数（带重试） =================
def request_ai(user_msg: str) -> str:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[{time.strftime('%H:%M:%S')}] 向 AI 发起请求 (第 {attempt + 1} 次尝试)...")
            resp = ai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。请直接输出内容。"},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=500,
                extra_body={"thinking": {"type": "disabled"}}
            )
            raw_content = resp.choices[0].message.content
            return raw_content if raw_content else "AI 这次没有回复内容"
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] AI 调用出错 (第 {attempt + 1} 次): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)  # 等待 3 秒后重试
            else:
                return f"AI 服务暂时不可用，请稍后再试~ (错误: {str(e)[:30]})"

# ================= QQ 机器人逻辑 =================
class MyBot(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        user_msg = message.content.strip()
        if not user_msg:
            return
        print(f"[{time.strftime('%H:%M:%S')}] 收到私聊消息: {user_msg}")
        start_time = time.time()
        answer = request_ai(user_msg)
        elapsed = round(time.time() - start_time, 2)
        print(f"[{time.strftime('%H:%M:%S')}] AI 回复耗时: {elapsed}秒")
        try:
            await message.reply(content=answer, msg_seq=1)
        except Exception as reply_err:
            print(f"[{time.strftime('%H:%M:%S')}] 私聊回复失败: {reply_err}")

    async def on_group_message_create(self, message: GroupMessage):
        user_msg = message.content.strip()
        if not user_msg.lower().startswith(TRIGGER_PREFIX):
            return
        actual_question = user_msg[len(TRIGGER_PREFIX):].strip()
        if not actual_question:
            await message.reply(content="请在 `.ai` 后面跟上你的问题哦~", msg_seq=1)
            return
        print(f"[{time.strftime('%H:%M:%S')}] 收到群聊 .ai 消息: {actual_question}")
        start_time = time.time()
        answer = request_ai(actual_question)
        elapsed = round(time.time() - start_time, 2)
        print(f"[{time.strftime('%H:%M:%S')}] AI 回复耗时: {elapsed}秒")
        try:
            await message.reply(content=answer, msg_seq=1)
        except Exception as reply_err:
            print(f"[{time.strftime('%H:%M:%S')}] 群聊回复失败: {reply_err}")

# ================= 启动入口 =================
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("正在启动 QQ 机器人...")
    intents = botpy.Intents(public_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

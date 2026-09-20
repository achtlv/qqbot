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
# 使用硅基流动全球节点，解决 Render 海外服务器访问国内节点慢的问题
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
QQ_APP_ID = os.environ.get("QQ_APP_ID")
QQ_APP_SECRET = os.environ.get("QQ_APP_SECRET")
TRIGGER_PREFIX = ".ai"

# 超时设为 30 秒，配合重试，避免单次卡死
ai = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0, max_retries=0)

# ================= Web 健康检查（保活用）=================
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================= 带重试的 AI 调用 =================
def request_ai(user_msg: str) -> str:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[{time.strftime('%H:%M:%S')}] 向 AI 请求 (第 {attempt + 1}/{max_retries} 次)...")
            resp = ai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。"},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=500
            )
            content = resp.choices[0].message.content
            print(f"[{time.strftime('%H:%M:%S')}] AI 返回成功")
            return content if content else "AI 这次没有回复内容"
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] AI 调用失败 (第 {attempt+1} 次): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待 2 秒后重试
            else:
                return f"AI 服务暂时不可用，请稍后再试~ (错误: {str(e)[:30]})"

# ================= QQ 机器人逻辑 =================
class MyBot(botpy.Client):
    # 私聊消息
    async def on_c2c_message_create(self, message: C2CMessage):
        user_msg = message.content.strip()
        if not user_msg:
            return
        print(f"[{time.strftime('%H:%M:%S')}] 收到私聊: {user_msg}")
        start = time.time()
        answer = request_ai(user_msg)
        print(f"[{time.strftime('%H:%M:%S')}] 耗时 {round(time.time()-start, 2)} 秒")
        try:
            await message.reply(content=answer, msg_seq=1)
        except Exception as e:
            print(f"私聊回复失败: {e}")

    # 群聊消息（以 .ai 开头）
    async def on_group_message_create(self, message: GroupMessage):
        user_msg = message.content.strip()
        if not user_msg.lower().startswith(TRIGGER_PREFIX):
            return
        actual_question = user_msg[len(TRIGGER_PREFIX):].strip()
        if not actual_question:
            await message.reply(content="请在 `.ai` 后面跟上你的问题哦~", msg_seq=1)
            return
        print(f"[{time.strftime('%H:%M:%S')}] 收到群聊: {actual_question}")
        start = time.time()
        answer = request_ai(actual_question)
        print(f"[{time.strftime('%H:%M:%S')}] 耗时 {round(time.time()-start, 2)} 秒")
        try:
            await message.reply(content=answer, msg_seq=1)
        except Exception as e:
            print(f"群聊回复失败: {e}")

# ================= 启动入口 =================
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("正在启动 QQ 机器人...")
    intents = botpy.Intents(public_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

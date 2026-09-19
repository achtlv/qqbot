import os
import botpy
from botpy.message import GroupMessage, C2CMessage
from openai import OpenAI
from fastapi import FastAPI
import uvicorn
import threading
import asyncio

# 从环境变量读取配置
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3.5-4B")

ai = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- FastAPI 健康检查服务（为了满足 Render 的 Web 服务要求）---
app = FastAPI()

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    # Render 会通过 PORT 环境变量指定端口
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- QQ 机器人逻辑 ---
class MyBot(botpy.Client):
    # 私聊消息
    async def on_c2c_message_create(self, message: C2CMessage):
        await self.handle_message(message, message.content)

    # 群聊 @ 消息
    async def on_group_at_message_create(self, message: GroupMessage):
        await self.handle_message(message, message.content)

    async def handle_message(self, message, content):
        user_msg = content.strip()
        if not user_msg: return
        try:
            resp = ai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复简洁有趣。"},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=500
            )
            answer = resp.choices[0].message.content
        except Exception as e:
            answer = f"AI 服务暂时出错啦：{str(e)}"
        await message.reply(content=answer)

def run_qq_bot():
    # 开启所有必要的心跳，支持私聊和群聊
    intents = botpy.Intents(public_messages=True, public_guild_messages=True, direct_message=True)
    client = MyBot(intents=intents)
    client.run(appid=os.environ.get("QQ_APP_ID"), secret=os.environ.get("QQ_APP_SECRET"))

if __name__ == "__main__":
    # 在后台线程启动健康检查服务
    threading.Thread(target=run_health_server, daemon=True).start()
    # 启动 QQ 机器人
    run_qq_bot()
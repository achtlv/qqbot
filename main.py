import os
import threading
import asyncio
import uvicorn
import botpy
from botpy.message import C2CMessage, GroupMessage
from openai import OpenAI
from fastapi import FastAPI

# ================= 配置区域 =================
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3.5-4B")
QQ_APP_ID = os.environ.get("QQ_APP_ID")
QQ_APP_SECRET = os.environ.get("QQ_APP_SECRET")

ai = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ================= Web 健康检查服务 (用于 Render 保活) =================
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================= AI 调用逻辑（抽离为独立函数） =================
def get_ai_reply(user_msg: str) -> str:
    """调用 AI 模型生成回复（同步阻塞函数）"""
    try:
        resp = ai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。"},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=500
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"AI 调用出错: {e}")
        return f"AI 服务暂时出错啦：{str(e)}"

# ================= QQ 机器人逻辑 =================
class MyBot(botpy.Client):
    # 1. 监听私聊消息
    async def on_c2c_message_create(self, message: C2CMessage):
        user_msg = message.content.strip()
        if not user_msg:
            return
        
        print(f"收到私聊消息: {user_msg}")
        
        # 使用 asyncio.to_thread 将同步的 AI 调用转为异步，防止阻塞消息循环
        answer = await asyncio.to_thread(get_ai_reply, user_msg)
        print(f"AI 回复: {answer}")

        # ✅ 修复：去掉 msg_id=message.id，因为底层 SDK 会自动处理，传了会报错。
        # 只保留 msg_seq=1，这是私聊回复必需的。
        await message.reply(content=answer, msg_seq=1)

    # 2. 监听群聊 @ 消息
    async def on_group_at_message_create(self, message: GroupMessage):
        # 剔除消息中的 @机器人 标记
        user_msg = message.content.replace(f"<@!{self.robot.id}>", "").strip()
        if not user_msg:
            return
        
        print(f"收到群聊消息: {user_msg}")
        
        answer = await asyncio.to_thread(get_ai_reply, user_msg)
        print(f"AI 回复: {answer}")

        # 群聊回复不需要传 msg_id 和 msg_seq
        await message.reply(content=answer)

# ================= 启动入口 =================
if __name__ == "__main__":
    # 1. 启动健康检查服务
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # 2. 启动 QQ 机器人
    print("正在启动 QQ 机器人...")
    intents = botpy.Intents(public_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

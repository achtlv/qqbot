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
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
MODEL_NAME = os.environ.get("MODEL_NAME", "glm-4.7-flash")
QQ_APP_ID = os.environ.get("QQ_APP_ID")
QQ_APP_SECRET = os.environ.get("QQ_APP_SECRET")

# 群聊触发前缀（不区分大小写）
TRIGGER_PREFIX = "/ai"

ai = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=45.0, max_retries=1)

# ================= Web 健康检查服务 =================
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================= 通用 AI 请求函数 =================
def request_ai(user_msg: str) -> str:
    """向 AI 发送请求，关闭思考模式，并处理错误"""
    try:
        resp = ai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。请直接输出内容，不要以空行开头。"},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=500,
            extra_body={
                "thinking": {
                    "type": "disabled"
                }
            }
        )
        raw_content = resp.choices[0].message.content
        return raw_content if raw_content else "AI 这次没有回复内容"
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] AI 调用出错: {e}")
        return f"AI 服务暂时出错啦：{str(e)[:50]}..."

# ================= QQ 机器人逻辑 =================
class MyBot(botpy.Client):
    # --- 私聊消息处理 ---
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
            print(f"[{time.strftime('%H:%M:%S')}] 私聊回复发送完毕。")
        except Exception as reply_err:
            print(f"[{time.strftime('%H:%M:%S')}] 私聊回复失败: {reply_err}")

    # --- 群聊全量消息处理（无需 @ 机器人）---
    async def on_group_message_create(self, message: GroupMessage):
        # 群聊中非 @ 机器人的消息不会带 <@!ID> 前缀，直接拿原文
        user_msg = message.content.strip()

        # 检查是否以 /ai 开头（不区分大小写）
        if not user_msg.lower().startswith(TRIGGER_PREFIX):
            # 不是 /ai 开头的消息，静默忽略，不回复
            print(f"[{time.strftime('%H:%M:%S')}] 群聊消息未匹配前缀，忽略: {user_msg[:30]}...")
            return

        # 去掉前缀，获取实际提问
        actual_question = user_msg[len(TRIGGER_PREFIX):].strip()
        if not actual_question:
            try:
                await message.reply(content="请在 `/ai` 后面跟上你的问题哦~", msg_seq=1)
            except Exception as e:
                print(f"回复空问题失败: {e}")
            return

        print(f"[{time.strftime('%H:%M:%S')}] 收到群聊 /ai 消息: {actual_question}")
        start_time = time.time()
        answer = request_ai(actual_question)
        elapsed = round(time.time() - start_time, 2)
        print(f"[{time.strftime('%H:%M:%S')}] AI 回复耗时: {elapsed}秒")
        try:
            await message.reply(content=answer, msg_seq=1)
            print(f"[{time.strftime('%H:%M:%S')}] 群聊回复发送完毕。")
        except Exception as reply_err:
            print(f"[{time.strftime('%H:%M:%S')}] 群聊回复失败: {reply_err}")

# ================= 启动入口 =================
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("正在启动 QQ 机器人...")
    # 需要监听群聊全量消息，使用 group_messages intent
    intents = botpy.Intents(public_messages=True, group_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

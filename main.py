import os
import time
import threading
import uvicorn
import botpy
from botpy.message import C2CMessage
from openai import OpenAI
from fastapi import FastAPI

# ================= 配置区域 =================
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3.5-4B")
QQ_APP_ID = os.environ.get("QQ_APP_ID")
QQ_APP_SECRET = os.environ.get("QQ_APP_SECRET")

# 将超时时间放宽到 45 秒，避免免费 API 偶尔排队导致超时
ai = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=45.0, max_retries=1)

# ================= Web 健康检查服务 =================
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================= QQ 机器人逻辑 =================
class MyBot(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        user_msg = message.content.strip()
        if not user_msg:
            return

        print(f"[{time.strftime('%H:%M:%S')}] 收到消息: {user_msg}")
        start_time = time.time()
        answer = "处理出错了"

        try:
            print(f"[{time.strftime('%H:%M:%S')}] 正在向 AI 请求...")
            resp = ai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。请直接输出内容，不要以空行开头。/no_think"},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=500
            )

            print(f"[{time.strftime('%H:%M:%S')}] AI 返回成功，正在解析...")
            raw_content = resp.choices[0].message.content

            if raw_content:
                answer = raw_content
            else:
                answer = "AI 这次没有回复内容"

            elapsed = round(time.time() - start_time, 2)
            print(f"[{time.strftime('%H:%M:%S')}] AI 回复耗时: {elapsed}秒")

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] AI 调用出错: {e}")
            answer = f"AI 服务暂时出错啦：{str(e)[:50]}..."

        try:
            print(f"[{time.strftime('%H:%M:%S')}] 正在发送 QQ 回复...")
            # 修复重点：去掉 msg_id=message.id，库会自动处理
            await message.reply(content=answer, msg_seq=1)
            print(f"[{time.strftime('%H:%M:%S')}] 回复发送完毕。")
        except Exception as reply_err:
            print(f"[{time.strftime('%H:%M:%S')}] 回复消息失败: {reply_err}")

# ================= 启动入口 =================
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("正在启动 QQ 机器人...")
    intents = botpy.Intents(public_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

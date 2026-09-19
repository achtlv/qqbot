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

# 初始化 AI 客户端，设置超时时间为 60 秒，最多重试 1 次
ai = OpenAI(
    api_key=API_KEY, 
    base_url=BASE_URL,
    timeout=60.0,
    max_retries=1
)

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
        start_time = time.time() # 记录开始时间

        try:
            resp = ai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    # 优化提示词：要求直接输出，不要以换行开头
                    {"role": "system", "content": "你是一个 QQ 里的 AI 助手，回复要简洁、有趣、热情。请直接输出内容，不要以空行或换行开头。"},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=500
            )
            
            # 去除首尾多余的换行符和空白符，完美解决换行问题！
            answer = resp.choices[0].message.content.strip()
            
            # 记录耗时
            elapsed = round(time.time() - start_time, 2)
            print(f"[{time.strftime('%H:%M:%S')}] AI 回复耗时: {elapsed}秒 | 内容: {answer}")
            
        except Exception as e:
            answer = f"AI 服务暂时出错啦：{str(e)}"
            print(f"[{time.strftime('%H:%M:%S')}] AI 调用出错: {e}")

        # 回复消息
        await message.reply(content=answer, msg_id=message.id, msg_seq=1)

# ================= 启动入口 =================
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("正在启动 QQ 机器人...")
    intents = botpy.Intents(public_messages=True)
    client = MyBot(intents=intents)
    client.run(appid=QQ_APP_ID, secret=QQ_APP_SECRET)

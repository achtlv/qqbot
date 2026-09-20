from fastapi import FastAPI, Request, Response
import httpx
import uvicorn
import os

app = FastAPI()
TARGET = "https://api.siliconflow.cn"  # 硅基流动国内节点

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{TARGET}/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            timeout=60.0
        )
    
    resp_headers = dict(resp.headers)
    for h in ["content-encoding", "transfer-encoding", "connection"]:
        resp_headers.pop(h, None)
        
    return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

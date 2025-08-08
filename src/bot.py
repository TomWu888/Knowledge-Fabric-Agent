import os
import sys
import traceback
import json
import aiohttp
import asyncio
import time
from typing import Any, Dict, Optional
from dataclasses import asdict

# 嘗試匯入 Azure AI Projects SDK
try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from azure.core.credentials import AzureKeyCredential
    AZURE_SDK_AVAILABLE = True
    print("✅ Azure AI Projects SDK 可用")
except ImportError:
    AZURE_SDK_AVAILABLE = False
    print("⚠️  Azure AI Projects SDK 不可用，將使用 REST API")

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.ai import AIOptions
from teams.ai.planners import AssistantsPlanner, OpenAIAssistantsOptions, AzureOpenAIAssistantsOptions
from teams.state import TurnState
from teams.feedback_loop_data import FeedbackLoopData

from config import Config

config = Config()

planner = AssistantsPlanner[TurnState](
    AzureOpenAIAssistantsOptions(
        api_key=config.AZURE_OPENAI_API_KEY,
        endpoint=config.AZURE_OPENAI_ENDPOINT,
        default_model=config.AZURE_OPENAI_MODEL_DEPLOYMENT_NAME,
        assistant_id=config.AZURE_OPENAI_ASSISTANT_ID)
)

# Define storage and application
storage = MemoryStorage()
bot_app = Application[TurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
        ai=AIOptions(planner=planner, enable_feedback_loop=True),
    )
)
    
@bot_app.ai.action("getCurrentWeather")
async def get_current_weather(context: TurnContext, state: TurnState):
    weatherData = {
        'San Francisco, CA': {
            'f': '71.6F',
            'c': '22C',
        },
        'Los Angeles': {
            'f': '75.2F',
            'c': '24C',
        },
    }
    location = context.data.get("location")
    if not weatherData.get(location):
        return f"No weather data for ${location} found"
    
    return weatherData[location][context.data.get("unit") if context.data.get("unit") else 'f']

@bot_app.ai.action("getNickname")
async def get_nickname(context: TurnContext, state: TurnState):
    nicknames = {
        'San Francisco, CA': 'The Golden City',
        'Los Angeles': 'LA',
    }
    location = context.data.get("location")
    
    return nicknames.get(location) if nicknames.get(location) else f"No nickname for ${location} found"

@bot_app.ai.action("queryFabricDataAgent")
async def query_fabric_data_agent(context: TurnContext, state: TurnState):
    """查詢 Azure AI Foundry 的 Fabric 數據代理程式"""
    print(f"調試 - queryFabricDataAgent 函數被呼叫")
    try:
        question = context.data.get("question", "")
        print(f"調試 - 收到的問題: {question}")
        if not question:
            print(f"調試 - 問題為空，返回錯誤訊息")
            return "請提供您的問題內容"
        
        # 檢查 Agent ID 是否有效
        print(f"調試 - 檢查 Agent ID: {config.AZURE_AI_FOUNDRY_AGENT_ID}")
        if not config.AZURE_AI_FOUNDRY_AGENT_ID or config.AZURE_AI_FOUNDRY_AGENT_ID == "":
            print(f"調試 - Agent ID 為空，將使用標準 Model 端點")
        
        # 嘗試使用 Azure AI Projects SDK
        if AZURE_SDK_AVAILABLE and config.AZURE_AI_FOUNDRY_AGENT_ID:
            return await call_azure_ai_foundry_agent_sdk(question)
        else:
            # 回退到 REST API 方式
            headers = {
                "api-key": config.AZURE_AI_FOUNDRY_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if config.AZURE_AI_FOUNDRY_AGENT_ID and config.AZURE_AI_FOUNDRY_AGENT_ID != "":
                return await call_azure_ai_foundry_agent(question, headers)
            else:
                return await call_azure_openai_model(question, headers)
            
    except aiohttp.ClientError as e:
        print(f"網路連接錯誤: {e}")
        return "網路連接錯誤，請檢查您的網路連接"
    except Exception as e:
        print(f"查詢 Fabric 數據代理程式時發生錯誤: {e}")
        return "查詢過程中發生錯誤，請稍後再試"

async def call_azure_ai_foundry_agent_sdk(question: str) -> str:
    """使用 Azure AI Projects SDK 呼叫 Agent"""
    try:
        print(f"調試 - 使用 Azure AI Projects SDK 呼叫 Agent")
        
        # 根據成功範例，使用正確的初始化方式
        project_connection_string = config.PROJECT_CONNECTION_STRING
        project_endpoint = config.PROJECT_ENDPOINT
        
        print(f"調試 - 使用端點: {project_endpoint}")
        print(f"調試 - 是否有 Connection String: {bool(project_connection_string)}")
        
        # 檢查 Azure 認證環境變數
        azure_client_id = os.environ.get("AZURE_CLIENT_ID", "")
        azure_client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
        azure_tenant_id = os.environ.get("AZURE_TENANT_ID", "")
        
        print(f"調試 - Azure 認證環境變數:")
        print(f"  - AZURE_CLIENT_ID: {'已設定' if azure_client_id else '未設定'}")
        print(f"  - AZURE_CLIENT_SECRET: {'已設定' if azure_client_secret else '未設定'}")
        print(f"  - AZURE_TENANT_ID: {'已設定' if azure_tenant_id else '未設定'}")
        
        # 根據成功範例，Azure AI Projects SDK 需要 TokenCredential
        # 嘗試使用 DefaultAzureCredential（支援 get_token）
        try:
            print(f"調試 - 嘗試使用 DefaultAzureCredential")
            credential = DefaultAzureCredential()
            project_client = AIProjectClient(
                endpoint=project_endpoint,
                credential=credential
            )
            print(f"調試 - 使用 DefaultAzureCredential 成功")
        except Exception as cred_error:
            print(f"調試 - DefaultAzureCredential 失敗: {cred_error}")
            
            # 如果 DefaultAzureCredential 失敗，嘗試使用環境變數認證
            if azure_client_id and azure_client_secret and azure_tenant_id:
                try:
                    print(f"調試 - 嘗試使用環境變數認證")
                    from azure.identity import ClientSecretCredential
                    credential = ClientSecretCredential(
                        tenant_id=azure_tenant_id,
                        client_id=azure_client_id,
                        client_secret=azure_client_secret
                    )
                    project_client = AIProjectClient(
                        endpoint=project_endpoint,
                        credential=credential
                    )
                    print(f"調試 - 使用環境變數認證成功")
                except Exception as env_error:
                    print(f"調試 - 環境變數認證失敗: {env_error}")
                    raise Exception("所有認證方式都失敗了")
            else:
                print(f"調試 - 環境變數未設定，無法使用 ClientSecretCredential")
                raise Exception("需要設定 Azure 認證環境變數或重新登入 Azure CLI")
        
        print(f"調試 - 成功初始化 AIProjectClient")
        
        # 測試連接
        try:
            connections = list(project_client.connections.list())
            print(f"調試 - 成功連接到 Azure AI Project，找到 {len(connections)} 個連接")
        except Exception as e:
            print(f"調試 - 無法列出連接，但客戶端初始化成功: {e}")
        
        # 獲取 Agent
        agent = project_client.agents.get_agent(config.AZURE_AI_FOUNDRY_AGENT_ID)
        print(f"調試 - 成功獲取 Agent: {agent.id}")
        
        # 建立 Thread
        thread = project_client.agents.threads.create()
        thread_id = thread.id
        print(f"調試 - 成功建立 Thread: {thread_id}")
        
        # 建立訊息
        message_obj = project_client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=question
        )
        print(f"調試 - 成功建立訊息: {message_obj.id}")
        
        # 建立並執行運行
        run = project_client.agents.runs.create(
            thread_id=thread_id,
            agent_id=agent.id
        )
        print(f"調試 - 成功建立運行: {run.id}")
        
        # 等待運行完成
        start_time = time.time()
        max_wait_time = 60  # 最多等待 60 秒
        
        while run.status in ["queued", "in_progress", "requires_action"]:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"調試 - 運行超時")
                return "Agent 運行超時，請稍後再試"
            
            await asyncio.sleep(1)
            print(f"調試 - 運行狀態: {run.status}")
            
            # 重新獲取運行狀態
            run = project_client.agents.runs.get(
                thread_id=thread_id,
                run_id=run.id
            )
        
        print(f"調試 - 運行完成，狀態: {run.status}")
        
        if run.status != "completed":
            error_msg = "未知錯誤"
            if hasattr(run, 'last_error') and run.last_error:
                error_msg = getattr(run.last_error, 'message', str(run.last_error))
            return f"Agent 運行失敗: {error_msg}"
        
        # 獲取回應訊息
        messages = list(project_client.agents.messages.list(thread_id=thread_id))
        print(f"調試 - 找到 {len(messages)} 條訊息")
        
        # 找到最新的助手回應
        assistant_message = None
        for msg in messages:
            if msg.role == "assistant":
                if not assistant_message or (
                    hasattr(msg, 'created_at') and hasattr(assistant_message, 'created_at') and
                    msg.created_at > assistant_message.created_at
                ):
                    assistant_message = msg
        
        if not assistant_message or not assistant_message.content:
            return "未找到助手回應"
        
        # 解析回應內容
        response_text = ""
        for content_item in assistant_message.content:
            if hasattr(content_item, 'text') and hasattr(content_item.text, 'value'):
                response_text += content_item.text.value
        
        if not response_text:
            return "無法提取回應文字，請稍後再試"
        
        print(f"調試 - 成功獲取回應 ({len(response_text)} 字元)")
        return f"**Fabric 數據代理程式回應：**\n\n{response_text}"
        
    except Exception as e:
        print(f"Azure AI Projects SDK 呼叫錯誤: {e}")
        
        # 提供具體的解決方案
        if "get_token" in str(e):
            print(f"調試 - 認證問題：需要 TokenCredential 而不是 AzureKeyCredential")
            print(f"調試 - 解決方案：")
            print(f"  1. 重新登入 Azure CLI: az login --scope https://ai.azure.com/.default")
            print(f"  2. 或設定環境變數:")
            print(f"     export AZURE_CLIENT_ID='your_client_id'")
            print(f"     export AZURE_CLIENT_SECRET='your_client_secret'")
            print(f"     export AZURE_TENANT_ID='your_tenant_id'")
        
        print(f"調試 - 回退到 REST API 方式")
        # 回退到 REST API 方式
        headers = {
            "api-key": config.AZURE_AI_FOUNDRY_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return await call_azure_ai_foundry_agent(question, headers)

async def call_azure_ai_foundry_agent(question: str, headers: dict) -> str:
    """使用 Azure AI Foundry Agent API 呼叫"""
    try:
        base_endpoint = config.AZURE_AI_FOUNDRY_ENDPOINT.rstrip('/')
        
        # 嘗試不同的 API 格式
        # 方法 1: 嘗試使用 OpenAI Assistants API 格式
        thread_endpoint = f"{base_endpoint}/openai/assistants/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads?api-version=2024-02-15-preview"
        thread_payload = {}
        
        print(f"調試 - 嘗試 OpenAI Assistants 格式，端點: {thread_endpoint}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(thread_endpoint, headers=headers, json=thread_payload) as response:
                print(f"調試 - Thread 建立回應狀態: {response.status}")
                
                if response.status == 201:
                    thread_result = await response.json()
                    thread_id = thread_result.get("id")
                    print(f"調試 - Thread ID: {thread_id}")
                    
                    # 步驟 2: 在 Thread 中發送訊息
                    message_endpoint = f"{base_endpoint}/openai/assistants/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/messages?api-version=2024-02-15-preview"
                    message_payload = {
                        "role": "user",
                        "content": question
                    }
                    
                    print(f"調試 - 發送訊息到 Thread，端點: {message_endpoint}")
                    
                    async with session.post(message_endpoint, headers=headers, json=message_payload) as msg_response:
                        print(f"調試 - 訊息發送回應狀態: {msg_response.status}")
                        
                        if msg_response.status == 201:
                            # 步驟 3: 執行 Agent
                            run_endpoint = f"{base_endpoint}/openai/assistants/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/runs?api-version=2024-02-15-preview"
                            run_payload = {}
                            
                            print(f"調試 - 執行 Agent，端點: {run_endpoint}")
                            
                            async with session.post(run_endpoint, headers=headers, json=run_payload) as run_response:
                                print(f"調試 - Agent 執行回應狀態: {run_response.status}")
                                
                                if run_response.status == 201:
                                    run_result = await run_response.json()
                                    run_id = run_result.get("id")
                                    print(f"調試 - Run ID: {run_id}")
                                    
                                    # 步驟 4: 等待執行完成並取得結果
                                    return await wait_for_run_completion_openai(base_endpoint, headers, thread_id, run_id)
                                else:
                                    error_text = await run_response.text()
                                    print(f"Agent 執行錯誤: {run_response.status} - {error_text}")
                                    return f"Agent 執行失敗，錯誤代碼: {run_response.status}"
                        else:
                            error_text = await msg_response.text()
                            print(f"訊息發送錯誤: {msg_response.status} - {error_text}")
                            return f"訊息發送失敗，錯誤代碼: {msg_response.status}"
                else:
                    error_text = await response.text()
                    print(f"Thread 建立錯誤: {response.status} - {error_text}")
                    print(f"調試 - 嘗試回退到標準 Model API")
                    return await call_azure_openai_model(question, headers)
                    
    except Exception as e:
        print(f"Azure AI Foundry Agent API 呼叫錯誤: {e}")
        print(f"調試 - 回退到標準 Model API")
        return await call_azure_openai_model(question, headers)

async def call_azure_openai_model(question: str, headers: dict) -> str:
    """使用標準 Azure OpenAI Model API 呼叫"""
    try:
        base_endpoint = config.AZURE_AI_FOUNDRY_ENDPOINT.rstrip('/')
        endpoint = f"{base_endpoint}/openai/deployments/{config.AZURE_AI_FOUNDRY_MODEL_NAME}/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "max_tokens": 4800,
            "temperature": 0.7,
            "stream": False
        }
        
        print(f"調試 - 使用標準 Model 端點: {endpoint}")
        print(f"調試 - 請求內容: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                print(f"調試 - 回應狀態: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"調試 - 完整 API 回應: {result}")
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if content:
                        print(f"調試 - 回應內容: {content}")
                        return f"**Fabric 數據代理程式回應：**\n\n{content}"
                    else:
                        print(f"調試 - 回應內容為空")
                        return "無法獲取有效的回應內容"
                else:
                    error_text = await response.text()
                    print(f"標準端點 API 錯誤: {response.status} - {error_text}")
                    return f"服務暫時無法使用，請稍後再試。錯誤代碼: {response.status}"
                    
    except Exception as e:
        print(f"標準 Model API 呼叫錯誤: {e}")
        return f"Model API 呼叫失敗: {str(e)}"

async def wait_for_run_completion_openai(base_endpoint: str, headers: dict, thread_id: str, run_id: str) -> str:
    """等待 OpenAI Assistants API 執行完成並取得結果"""
    try:
        # 檢查執行狀態
        status_endpoint = f"{base_endpoint}/openai/assistants/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/runs/{run_id}?api-version=2024-02-15-preview"
        
        max_attempts = 30  # 最多等待 30 次
        attempt = 0
        
        while attempt < max_attempts:
            async with aiohttp.ClientSession() as session:
                async with session.get(status_endpoint, headers=headers) as response:
                    if response.status == 200:
                        run_status = await response.json()
                        status = run_status.get("status")
                        print(f"調試 - Run 狀態: {status}")
                        
                        if status == "completed":
                            # 取得執行結果
                            messages_endpoint = f"{base_endpoint}/openai/assistants/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/messages?api-version=2024-02-15-preview"
                            
                            async with session.get(messages_endpoint, headers=headers) as msg_response:
                                if msg_response.status == 200:
                                    messages_result = await msg_response.json()
                                    messages = messages_result.get("data", [])
                                    
                                    # 取得最新的 assistant 訊息
                                    for message in messages:
                                        if message.get("role") == "assistant":
                                            content = message.get("content", [])
                                            if content and len(content) > 0:
                                                text_content = content[0].get("text", {}).get("value", "")
                                                if text_content:
                                                    return f"**Fabric 數據代理程式回應：**\n\n{text_content}"
                            
                            return "執行完成但無法取得回應內容"
                        elif status in ["failed", "cancelled", "expired"]:
                            return f"Agent 執行失敗，狀態: {status}"
                        else:
                            # 繼續等待
                            await asyncio.sleep(2)  # 等待 2 秒
                            attempt += 1
                    else:
                        error_text = await response.text()
                        print(f"檢查執行狀態錯誤: {response.status} - {error_text}")
                        return f"檢查執行狀態失敗，錯誤代碼: {response.status}"
        
        return "執行超時，請稍後再試"
        
    except Exception as e:
        print(f"等待執行完成時發生錯誤: {e}")
        return f"等待執行完成失敗: {str(e)}"

async def wait_for_run_completion(base_endpoint: str, headers: dict, thread_id: str, run_id: str) -> str:
    """等待 Agent 執行完成並取得結果"""
    try:
        # 檢查執行狀態
        status_endpoint = f"{base_endpoint}/agents/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/runs/{run_id}?api-version=2024-02-15-preview"
        
        max_attempts = 30  # 最多等待 30 次
        attempt = 0
        
        while attempt < max_attempts:
            async with aiohttp.ClientSession() as session:
                async with session.get(status_endpoint, headers=headers) as response:
                    if response.status == 200:
                        run_status = await response.json()
                        status = run_status.get("status")
                        print(f"調試 - Run 狀態: {status}")
                        
                        if status == "completed":
                            # 取得執行結果
                            messages_endpoint = f"{base_endpoint}/agents/{config.AZURE_AI_FOUNDRY_AGENT_ID}/threads/{thread_id}/messages?api-version=2024-02-15-preview"
                            
                            async with session.get(messages_endpoint, headers=headers) as msg_response:
                                if msg_response.status == 200:
                                    messages_result = await msg_response.json()
                                    messages = messages_result.get("data", [])
                                    
                                    # 取得最新的 assistant 訊息
                                    for message in messages:
                                        if message.get("role") == "assistant":
                                            content = message.get("content", [])
                                            if content and len(content) > 0:
                                                text_content = content[0].get("text", {}).get("value", "")
                                                if text_content:
                                                    return f"**Fabric 數據代理程式回應：**\n\n{text_content}"
                            
                            return "執行完成但無法取得回應內容"
                        elif status in ["failed", "cancelled", "expired"]:
                            return f"Agent 執行失敗，狀態: {status}"
                        else:
                            # 繼續等待
                            await asyncio.sleep(2)  # 等待 2 秒
                            attempt += 1
                    else:
                        error_text = await response.text()
                        print(f"檢查執行狀態錯誤: {response.status} - {error_text}")
                        return f"檢查執行狀態失敗，錯誤代碼: {response.status}"
        
        return "執行超時，請稍後再試"
        
    except Exception as e:
        print(f"等待執行完成時發生錯誤: {e}")
        return f"等待執行完成失敗: {str(e)}"

@bot_app.error
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The agent encountered an error or bug.")

@bot_app.feedback_loop()
async def feedback_loop(_context: TurnContext, _state: TurnState, feedback_loop_data: FeedbackLoopData):
    # Add custom feedback process logic here.
    print(f"Your feedback is:\n{json.dumps(asdict(feedback_loop_data), indent=4)}")
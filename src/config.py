"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot Configuration"""

    PORT = 3978
    APP_ID = os.environ.get("BOT_ID", "")
    APP_PASSWORD = os.environ.get("BOT_PASSWORD", "")
    APP_TYPE = os.environ.get("BOT_TYPE", "")
    APP_TENANTID = os.environ.get("BOT_TENANT_ID", "")
    AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"] # Azure OpenAI API key
    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"] # Azure OpenAI endpoint
    AZURE_OPENAI_MODEL_DEPLOYMENT_NAME = os.environ["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME"] # Azure OpenAI deployment model name
    AZURE_OPENAI_ASSISTANT_ID = os.environ["AZURE_OPENAI_ASSISTANT_ID"] # Azure OpenAI Assistant ID
    
    # Azure AI Foundry Configuration
    AZURE_AI_FOUNDRY_ENDPOINT = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "https://aiagent-3799-resource.services.ai.azure.com")
    AZURE_AI_FOUNDRY_API_KEY = os.environ.get("AZURE_AI_FOUNDRY_API_KEY", "3UI08E81wcAeOP0y4iOwwG8p7V5xkfnsq5nVs1xtEYJC8defR6YYJQQJ99BEACHYHv6XJ3w3AAAAACOGx3Tv")
    AZURE_AI_FOUNDRY_MODEL_NAME = os.environ.get("AZURE_AI_FOUNDRY_MODEL_NAME", "gpt-4o")
    AZURE_AI_FOUNDRY_AGENT_ID = os.environ.get("AZURE_AI_FOUNDRY_AGENT_ID", "asst_S74Ble30h4iGQ001UAx9n7SF")
    
    # Azure AI Foundry Project Configuration (根據成功範例)
    PROJECT_CONNECTION_STRING = os.environ.get("PROJECT_CONNECTION_STRING", "")
    # 使用基礎端點，讓 SDK 自動處理路徑
    PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "https://aiagent-3799-resource.services.ai.azure.com")

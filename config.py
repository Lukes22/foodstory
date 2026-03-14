import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-fallback-key')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///foodstory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api-inference.modelscope.cn/v1/')
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL = os.getenv('AI_MODEL', 'Qwen/Qwen3-32B')
    AI_ENABLE_THINKING = True
    AI_THINKING_BUDGET = 4096

    DEFAULT_HEALTH = 100
    DEFAULT_SANITY = 100
    DEFAULT_STRENGTH = 100

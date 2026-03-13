import os
import sys
import requests

# 将项目根目录添加到系统路径，以便可以导入内部模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger('list_gemini_models')

def fetch_and_log_models():
    api_key = settings.GOOGLE_AI_KEY
    if not api_key:
        logger.error("在配置中未找到 GOOGLE_AI_KEY！请检查环境变量或 settings 配置。")
        return
        
    # 根据 llm_client.py 中的接口路径，调用获取模型列表的接口
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    logger.info("正在查询可用的 Gemini 模型列表...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        models = data.get("models", [])
        
        # 我们主要关注名字里带有 gemini 的模型
        gemini_models = [m for m in models if "gemini" in m.get("name", "").lower()]
        
        logger.info(f"成功获取模型列表！共筛选出 {len(gemini_models)} 个包含 'gemini' 的模型。")
        logger.info("=" * 50)
        logger.info("建议可用的模型名称 (Model IDs):")
        logger.info("-" * 50)
        
        for m in gemini_models:
            raw_name = m.get("name", "Unknown")
            model_id = raw_name.replace('models/', '')
            logger.info(f"- {model_id}")
            
        logger.info("=" * 50)
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"获取模型列表失败 HTTP Error: {e}，可能原因：API Key 无效或接口调整。")
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求错误，请检查网络或代理设置: {e}")
    except Exception as e:
        logger.error(f"发生未知错误: {e}")

if __name__ == "__main__":
    fetch_and_log_models()

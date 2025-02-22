import os
import json
import requests
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_llama_result(api_key: str, job_id: str):
    """獲取並顯示 LlamaParse 結果的完整結構"""
    base_url = "https://api.cloud.llamaindex.ai/api/parsing"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # 獲取結果
    response = requests.get(
        f"{base_url}/job/{job_id}/result/json",
        headers=headers
    )
    response.raise_for_status()
    result = response.json()
    
    # 保存完整的 JSON 結果
    with open('llama_output.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("已保存完整的 JSON 結果到 llama_output.json")
    
    # 分析結構
    total_pages = len(result['pages'])
    total_items = sum(len(page.get('items', [])) for page in result['pages'])
    
    # 顯示統計資訊
    stats = {
        "總頁數": total_pages,
        "總項目數": total_items,
        "頁面結構": {
            "第一頁示例": {
                "可用欄位": list(result['pages'][0].keys()),
                "項目類型": list(set(item['type'] for item in result['pages'][0].get('items', [])))
            }
        }
    }
    logger.info(f"LlamaParse 輸出統計：\n{json.dumps(stats, ensure_ascii=False, indent=2)}")

def main():
    load_dotenv()
    api_key = os.getenv("LLAMA_PARSE_API_KEY")
    
    if not api_key:
        raise ValueError("請設定 LLAMA_PARSE_API_KEY 環境變數")
    
    # 使用已知的 job_id
    job_id = "39a17740-8678-483e-9617-8022795c67e4"
    
    get_llama_result(api_key, job_id)

if __name__ == "__main__":
    main()

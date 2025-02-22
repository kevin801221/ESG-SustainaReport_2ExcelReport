import os
import json
import requests
import logging
from dotenv import load_dotenv

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_result(api_key: str, job_id: str):
    """獲取並顯示解析結果的結構"""
    base_url = "https://api.cloud.llamaindex.ai/api/parsing"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # 獲取結果
    response = requests.get(
        f"{base_url}/job/{job_id}/result/json",
        headers=headers
    )
    response.raise_for_status()
    result = response.json()
    
    # 分析並顯示結構
    print("\n=== JSON 結構分析 ===")
    for page in result["pages"]:
        print(f"\n第 {page['page']} 頁:")
        if "items" in page:
            for item in page["items"]:
                if item["type"] == "text":
                    print("\n文字內容片段:")
                    print(item["value"][:200] + "..." if len(item["value"]) > 200 else item["value"])
                    print("-" * 50)
                elif item["type"] == "table":
                    print("\n表格內容:")
                    print(json.dumps(item["value"], ensure_ascii=False, indent=2))
                    print("-" * 50)

def main():
    load_dotenv()
    api_key = os.getenv("LLAMA_PARSE_API_KEY")
    
    if not api_key:
        raise ValueError("請設定 LLAMA_PARSE_API_KEY 環境變數")
    
    # 使用已知的 job_id
    job_id = "39a17740-8678-483e-9617-8022795c67e4"
    
    get_result(api_key, job_id)

if __name__ == "__main__":
    main()

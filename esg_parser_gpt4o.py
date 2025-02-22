import os
import json
import pandas as pd
import numpy as np
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ESGParser:
    def __init__(self, llama_api_key: str, openai_api_key: str):
        self.llama_api_key = llama_api_key
        self.llama_base_url = "https://api.cloud.llamaindex.ai/api/parsing"
        self.llama_headers = {"Authorization": f"Bearer {llama_api_key}"}
        
        # 初始化 OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        
        # LLM 系統提示
        self.system_prompt = """你是一個專業的 ESG 報告分析專家。你的任務是從 ESG 報告中提取關鍵資訊，並按照以下結構整理：

1. 章節 (chapter)：必須是以下其中之一
   - 導言（前言、董事長的話、關於報告等）
   - 實踐永續管理（永續目標、ESG策略等）
   - 營運與治理（公司治理、經濟績效等）
   - 環境永續（環保、節能、減碳等）
   - 社會共融（員工照顧、社會參與等）
   - 附錄

2. 資料來源 (source)：必須是以下其中之一
   - 摘要（重點內容）
   - 內文（主要說明文字）
   - 圖表（數據統計）
   - 註釋（補充說明）

3. 項目 (item)：
   - 提取所有關鍵的 ESG 指標或重要敘述
   - 特別注意以下類型的資訊：
     * 評比結果（如 MSCI、CDP 等評級）
     * 具體目標（如減碳目標、用水目標等）
     * 成果數據（如節能減碳成效、社會投資金額等）
     * 重要政策（如環境政策、人權政策等）
   - 確保項目描述清晰完整
   - 避免重複或過於籠統的描述

4. 數據 (value)：
   - 提取所有具體的數字、指標和評級
   - 包含完整的：
     * 數值（如 "100"）
     * 單位（如 "%"、"小時"、"百萬元"）
     * 時間資訊（如 "2024年"）
     * 變化資訊（如 "較去年增加10%"）
   - 如果項目沒有具體數據，請填入 null（不要留空字串或填入 "N/A"）

分析要求：
1. 完整性：不要遺漏任何關鍵資訊
2. 準確性：確保數據和描述的對應關係正確
3. 結構性：確保資訊被正確分類到對應章節
4. 去重複：合併相似或重複的資訊
5. 格式檢查：確保輸出的 JSON 格式正確

請用以下 JSON 格式回覆：
{
    "items": [
        {
            "chapter": "章節名稱",
            "source": "資料來源",
            "item": "項目名稱",
            "value": "數據值"
        }
    ]
}"""

        # 資料整合提示
        self.integration_prompt = """請整合以下 ESG 報告的分析結果。

整合規則：
1. 移除完全重複的項目
2. 合併相似項目，保留更完整的描述
3. 統一數據格式和單位
4. 確保時間序列的一致性
5. 保持資訊的完整性和準確性

輸入的分析結果如下：
{previous_results}

請提供整合後的結果，使用相同的 JSON 格式：
{
    "items": [
        {
            "chapter": "章節名稱",
            "source": "資料來源",
            "item": "項目名稱",
            "value": "數據值"
        }
    ]
}

注意：
1. 確保輸出是有效的 JSON 格式
2. 數據值如果不存在應該是 null，不要使用空字串
3. 確保所有必要欄位都存在
4. 避免特殊字符或跳脫字符造成的解析錯誤"""

    def get_result(self, job_id: str) -> Dict:
        """獲取解析結果"""
        logger.info(f"獲取解析結果: {job_id}")
        response = requests.get(
            f"{self.llama_base_url}/job/{job_id}/result/json",
            headers=self.llama_headers
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_with_gpt4(self, text: str, page_num: int) -> List[Dict]:
        """使用 GPT-4 分析內容"""
        try:
            # 添加頁碼和內容長度資訊
            content = f"第 {page_num} 頁（共 {len(text)} 字）內容：\n\n{text}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"請分析以下ESG報告內容：\n\n{content}"}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            # 解析回應
            result = json.loads(response.choices[0].message.content)
            items = result.get('items', [])
            
            # 驗證每個項目的格式
            validated_items = []
            for item in items:
                if all(k in item for k in ['chapter', 'source', 'item', 'value']):
                    validated_items.append(item)
                else:
                    logger.warning(f"跳過格式不正確的項目: {item}")
            
            return validated_items
            
        except Exception as e:
            logger.error(f"GPT-4 分析失敗: {str(e)}")
            return []
    
    def integrate_results(self, all_results: List[Dict]) -> List[Dict]:
        """整合所有分析結果"""
        try:
            # 將之前的結果轉換為 JSON 字符串，確保正確的格式化
            results_dict = {"items": all_results}
            previous_results = json.dumps(results_dict, ensure_ascii=False, indent=2)
            
            # 使用 GPT-4 整合結果
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.integration_prompt.format(
                        previous_results=previous_results
                    )}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            # 解析回應並驗證
            content = response.choices[0].message.content.strip()
            if not content.startswith('{'):
                content = content[content.find('{'):]
            result = json.loads(content)
            items = result.get('items', [])
            
            # 驗證每個項目的格式
            validated_items = []
            for item in items:
                if all(k in item for k in ['chapter', 'source', 'item', 'value']):
                    validated_items.append(item)
                else:
                    logger.warning(f"整合時跳過格式不正確的項目: {item}")
            
            return validated_items
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤: {str(e)}")
            return all_results
        except Exception as e:
            logger.error(f"結果整合失敗: {str(e)}")
            return all_results
    
    def clean_text(self, text: str) -> str:
        """清理文本，移除多餘的空白和特殊字符"""
        # 替換多個空白為單個空白
        text = ' '.join(text.split())
        # 移除可能導致 JSON 解析錯誤的字符
        text = text.replace('\u2028', ' ').replace('\u2029', ' ')
        return text.strip()
    
    def process_content(self, result: Dict) -> List[Dict]:
        """處理所有內容"""
        all_results = []
        total_pages = len(result['pages'])
        logger.info(f"開始處理內容，總頁數：{total_pages}")
        
        # 逐頁處理
        for page in result['pages']:
            page_num = page['page']
            logger.info(f"處理第 {page_num} 頁")
            
            if 'items' in page:
                page_text = []
                for item in page['items']:
                    if item['type'] == 'text':
                        text = self.clean_text(item['value'])
                        if text:
                            page_text.append(text)
                
                # 將整頁內容一起送給 GPT-4 分析
                if page_text:
                    text_to_analyze = '\n'.join(page_text)
                    results = self.analyze_with_gpt4(text_to_analyze, page_num)
                    all_results.extend(results)
        
        logger.info(f"內容處理完成，開始整合結果")
        
        # 整合所有結果
        integrated_results = self.integrate_results(all_results)
        
        return integrated_results
    
    def save_to_excel(self, data: List[Dict], excel_path: str):
        """保存到 Excel"""
        logger.info(f"保存結果到 Excel: {excel_path}")
        
        # 創建 DataFrame
        df = pd.DataFrame(data)
        
        # 移除重複的行
        df = df.drop_duplicates()
        
        # 根據章節和資料來源排序
        df = df.sort_values(['chapter', 'source', 'item'])
        
        # 重命名欄位
        df = df.rename(columns={
            'chapter': '章節',
            'source': '資料來源',
            'item': '項目',
            'value': '數據'
        })
        
        # 保存到 Excel
        writer = pd.ExcelWriter(excel_path, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='ESG報告內容')
        
        # 調整格式
        workbook = writer.book
        worksheet = writer.sheets['ESG報告內容']
        
        # 設定列寬
        column_widths = {
            'A': 15,  # 章節
            'B': 10,  # 資料來源
            'C': 40,  # 項目
            'D': 30   # 數據（增加寬度以顯示更多資訊）
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
        
        # 保存
        writer.close()
        
        # 顯示統計信息
        stats = {
            "章節數": int(len(df['章節'].unique())),
            "資料來源數": int(len(df['資料來源'].unique())),
            "項目數": int(len(df['項目'].unique())),
            "有數據的項目數": int(df['數據'].notna().sum()),
            "總條目數": int(len(df))
        }
        logger.info(f"統計資訊: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    def process_pdf(self, excel_path: str, job_id: str):
        """處理 PDF 文件的主要函數"""
        try:
            # 獲取結果
            result = self.get_result(job_id)
            
            # 處理內容
            data = self.process_content(result)
            
            # 保存到 Excel
            self.save_to_excel(data, excel_path)
            
        except Exception as e:
            logger.error(f"處理過程中發生錯誤: {str(e)}")
            raise

def main():
    load_dotenv()
    llama_api_key = os.getenv("LLAMA_PARSE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not llama_api_key or not openai_api_key:
        raise ValueError("請設定 LLAMA_PARSE_API_KEY 和 OPENAI_API_KEY 環境變數")
    
    parser = ESGParser(llama_api_key, openai_api_key)
    
    # 使用已知的 job_id
    job_id = "39a17740-8678-483e-9617-8022795c67e4"
    
    parser.process_pdf(
        excel_path="example/tsmc_esg_gpt4o.xlsx",
        job_id=job_id
    )

if __name__ == "__main__":
    main()

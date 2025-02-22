#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ESG 報告處理工具

這個腳本整合了 PDF 上傳和解析的功能，讓使用者可以一次完成整個處理流程。
主要功能：
1. 上傳 PDF 文件到 LlamaParse API
2. 等待解析完成
3. 使用 GPT-4 分析內容
4. 輸出結構化的 Excel 文件

使用方法：
python process_esg_report.py --pdf path/to/your/report.pdf --output path/to/output.xlsx

作者：Codeium AI Team
日期：2025-02-22
"""

import os
import sys
import time
import logging
import argparse
import requests
from typing import Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
from esg_parser_gpt4o import ESGParser

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ESGReportProcessor:
    """ESG 報告處理器，整合上傳和解析功能"""
    
    def __init__(self):
        """初始化處理器，載入環境變數"""
        # 載入環境變數
        load_dotenv()
        
        # 獲取 API 金鑰
        self.llama_api_key = os.getenv("LLAMA_PARSE_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # 檢查 API 金鑰是否存在
        if not self.llama_api_key or not self.openai_api_key:
            raise ValueError(
                "請確保已設定以下環境變數：\n"
                "1. LLAMA_PARSE_API_KEY\n"
                "2. OPENAI_API_KEY"
            )
        
        # LlamaParse API 設定
        self.llama_base_url = "https://api.cloud.llamaindex.ai/api/parsing"
        self.llama_headers = {"Authorization": f"Bearer {self.llama_api_key}"}
    
    def upload_pdf(self, pdf_path: str) -> str:
        """
        上傳 PDF 文件到 LlamaParse API
        
        參數：
            pdf_path (str): PDF 文件的路徑
            
        返回：
            str: 上傳任務的 job_id
            
        異常：
            FileNotFoundError: 找不到 PDF 文件
            requests.exceptions.RequestException: API 請求失敗
        """
        logger.info(f"開始上傳 PDF: {pdf_path}")
        
        # 檢查文件是否存在
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")
        
        # 上傳文件
        try:
            with open(pdf_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{self.llama_base_url}/upload",
                    headers=self.llama_headers,
                    files=files
                )
            response.raise_for_status()
            job_id = response.json()["job_id"]
            logger.info(f"PDF 上傳成功，job_id: {job_id}")
            return job_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PDF 上傳失敗: {str(e)}")
            raise
    
    def check_job_status(self, job_id: str) -> Tuple[bool, Optional[str]]:
        """
        檢查 LlamaParse 解析任務的狀態
        
        參數：
            job_id (str): 要檢查的任務 ID
            
        返回：
            Tuple[bool, Optional[str]]:
            - bool: 任務是否完成
            - Optional[str]: 如果有錯誤，返回錯誤訊息
        """
        try:
            response = requests.get(
                f"{self.llama_base_url}/job/{job_id}/status",
                headers=self.llama_headers
            )
            response.raise_for_status()
            status = response.json()
            
            # 檢查是否完成
            if status.get("status") == "completed":
                return True, None
            # 檢查是否失敗
            elif status.get("status") == "failed":
                return True, status.get("error", "未知錯誤")
            # 還在處理中
            else:
                return False, None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"檢查任務狀態失敗: {str(e)}")
            return False, str(e)
    
    def wait_for_completion(self, job_id: str, check_interval: int = 5, timeout: int = 300) -> bool:
        """
        等待 LlamaParse 解析任務完成
        
        參數：
            job_id (str): 要等待的任務 ID
            check_interval (int): 檢查間隔（秒）
            timeout (int): 最長等待時間（秒）
            
        返回：
            bool: 任務是否成功完成
        """
        logger.info(f"等待解析完成，最多等待 {timeout} 秒")
        start_time = time.time()
        
        while True:
            # 檢查是否超時
            if time.time() - start_time > timeout:
                logger.error("等待超時")
                return False
            
            # 檢查狀態
            is_done, error = self.check_job_status(job_id)
            
            # 如果完成且沒有錯誤
            if is_done and not error:
                logger.info("解析完成")
                return True
            # 如果有錯誤
            elif error:
                logger.error(f"解析失敗: {error}")
                return False
            
            # 等待後再檢查
            logger.info(f"解析中...（已等待 {int(time.time() - start_time)} 秒）")
            time.sleep(check_interval)
    
    def process_report(self, pdf_path: str, output_path: str) -> bool:
        """
        處理 ESG 報告的主要函數
        
        參數：
            pdf_path (str): PDF 文件的路徑
            output_path (str): Excel 輸出的路徑
            
        返回：
            bool: 處理是否成功
        """
        try:
            # 1. 上傳 PDF
            job_id = self.upload_pdf(pdf_path)
            
            # 2. 等待解析完成
            if not self.wait_for_completion(job_id):
                return False
            
            # 3. 使用 GPT-4 分析內容
            logger.info("開始使用 GPT-4 分析內容")
            parser = ESGParser(self.llama_api_key, self.openai_api_key)
            parser.process_pdf(output_path, job_id)
            
            logger.info(f"處理完成，結果已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"處理過程中發生錯誤: {str(e)}")
            return False

def main():
    """主程式入口"""
    # 解析命令列參數
    parser = argparse.ArgumentParser(description="ESG 報告處理工具")
    parser.add_argument(
        "--pdf",
        required=True,
        help="PDF 報告的路徑"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Excel 輸出的路徑"
    )
    args = parser.parse_args()
    
    # 建立輸出目錄（如果不存在）
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 處理報告
    processor = ESGReportProcessor()
    success = processor.process_report(args.pdf, args.output)
    
    # 設定退出碼
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

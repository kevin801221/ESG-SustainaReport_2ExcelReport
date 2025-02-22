# ESG 報告解析工具

這是一個強大的工具，用於將 ESG（環境、社會和公司治理）PDF 報告轉換為結構化 Excel 文件。該工具結合了 LlamaParse 的 PDF 解析能力和 GPT-4 的智能分析能力，能夠自動提取和組織 ESG 報告中的關鍵資訊。

## 功能特點

- **智能 PDF 解析**：使用 LlamaParse API 進行精確的 PDF 文本提取
- **GPT-4 分析**：使用最新的 GPT-4 模型進行深度文本理解
- **結構化輸出**：自動將資訊整理為四個維度
  - 章節：文件的主要分類
  - 資料來源：內容的類型
  - 項目：具體的 ESG 指標或描述
  - 數據：相關的數值資料
- **自動格式化**：生成美觀的 Excel 報表

## 快速開始

### 1. 環境設定

首先，確保你有 Python 3.8 或更新版本，然後按照以下步驟設定環境：

```bash
# 建立虛擬環境
python -m venv esg_env

# 啟動虛擬環境
source esg_env/bin/activate  # macOS/Linux
.\esg_env\Scripts\activate   # Windows

# 安裝依賴套件
pip install openai pandas python-dotenv requests openpyxl
```

### 2. API 金鑰設定

在專案根目錄建立 `.env` 檔案：

```plaintext
LLAMA_PARSE_API_KEY=your_llama_parse_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 3. 使用方法

我們提供了兩種使用方式：一體化處理和分步驟處理。

#### 方法一：一體化處理（推薦）

使用 `process_esg_report.py` 一次完成所有步驟：

```bash
# 處理單個報告
python process_esg_report.py --pdf path/to/your/report.pdf --output path/to/output.xlsx

# 例如：
python process_esg_report.py --pdf example/tsmc_esg.pdf --output example/tsmc_esg_result.xlsx
```

這個腳本會：
1. 自動上傳 PDF 到 LlamaParse
2. 等待解析完成（預設最多等 5 分鐘）
3. 使用 GPT-4 分析內容
4. 輸出 Excel 檔案

處理多個報告：
```bash
# 使用 shell 腳本
for pdf in reports/*.pdf; do
    output="results/$(basename "$pdf" .pdf).xlsx"
    python process_esg_report.py --pdf "$pdf" --output "$output"
done
```

#### 方法二：分步驟處理

如果你需要更多控制或想要查看中間結果，可以分步驟處理：

1. 上傳 PDF：
```python
import os
from dotenv import load_dotenv
import requests

def upload_pdf(pdf_path):
    load_dotenv()
    api_key = os.getenv("LLAMA_PARSE_API_KEY")
    
    url = "https://api.cloud.llamaindex.ai/api/parsing/upload"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    with open(pdf_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, headers=headers, files=files)
    
    response.raise_for_status()
    return response.json()["job_id"]

# 使用方法
pdf_path = "path/to/your/esg_report.pdf"
job_id = upload_pdf(pdf_path)
print(f"Job ID: {job_id}")
```

2. 解析內容：
```python
from esg_parser_gpt4o import ESGParser

parser = ESGParser(llama_api_key, openai_api_key)
parser.process_pdf(
    excel_path="example/your_report_name.xlsx",
    job_id="your_job_id_here"
)
```

## 輸出格式說明

### 章節分類

- **導言**：前言、董事長的話、關於報告等
- **實踐永續管理**：永續目標、ESG策略等
- **營運與治理**：公司治理、經濟績效等
- **環境永續**：環保、節能、減碳等
- **社會共融**：員工照顧、社會參與等
- **附錄**：補充資料

### 資料來源分類

- **摘要**：重點內容
- **內文**：主要說明文字
- **圖表**：數據統計
- **註釋**：補充說明

### 數據格式

數據欄位包含：
- 具體數值
- 單位（如：%、元、小時等）
- 時間資訊（如：2024年）
- 變化資訊（如：較去年增加10%）

## 使用建議

1. **PDF 品質要求**：
   - 使用文字版 PDF，避免掃描版
   - 確保 PDF 格式正確，沒有加密
   - 避免使用有複雜表格或圖形的 PDF

2. **最佳實踐**：
   - 先用小型文件測試系統
   - 定期備份重要的輸出結果
   - 檢查輸出的數據準確性

3. **效能優化**：
   - 使用一體化處理腳本以減少手動步驟
   - 批次處理多個文件時使用腳本自動化
   - 適當設定等待時間和重試次數

## 常見問題解決

1. **上傳失敗**：
   - 檢查 API 金鑰是否正確
   - 確認 PDF 文件是否可以訪問
   - 檢查網路連接狀態

2. **解析超時**：
   - 增加 `wait_for_completion` 的 timeout 參數
   - 檢查 PDF 文件大小是否合適
   - 考慮分割大型文件

3. **數據提取不完整**：
   - 檢查 PDF 文字是否可選取
   - 調整 GPT-4 的提示詞
   - 使用更新版本的 PDF

## 進階功能

### 自訂等待時間

```python
# 在 process_esg_report.py 中設定
processor.wait_for_completion(
    job_id,
    check_interval=10,  # 每 10 秒檢查一次
    timeout=600        # 最多等待 10 分鐘
)
```

### 批次處理腳本

```python
# batch_process.py
import os
from process_esg_report import ESGReportProcessor

def process_directory(input_dir, output_dir):
    processor = ESGReportProcessor()
    
    # 處理所有 PDF 文件
    for pdf_file in os.listdir(input_dir):
        if pdf_file.endswith('.pdf'):
            pdf_path = os.path.join(input_dir, pdf_file)
            excel_path = os.path.join(
                output_dir,
                pdf_file.replace('.pdf', '.xlsx')
            )
            processor.process_report(pdf_path, excel_path)

# 使用方法
process_directory('input_pdfs', 'output_excels')
```

## 版本歷史

### v1.1.0 (2025-02-22)
- 新增一體化處理腳本
- 改進錯誤處理
- 添加批次處理功能

### v1.0.0 (2025-02-22)
- 初始版本發布
- 支援基本的 PDF 解析和 GPT-4 分析
- 提供 Excel 輸出功能

## 貢獻指南

歡迎提供改進建議和 bug 回報。請在提交問題時提供：
- 使用的 PDF 文件特徵
- 完整的錯誤訊息
- 重現問題的步驟

## 授權

本專案採用 MIT 授權條款。

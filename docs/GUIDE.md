# selftest — 韌體驗證腳本自動測試工具

> 版本：0.1.0 | Python 3.9+

## 目錄

- [簡介](#簡介)
- [架構總覽](#架構總覽)
- [Pipeline 流程](#pipeline-流程)
- [安裝](#安裝)
- [快速開始](#快速開始)
- [CLI 指令參考](#cli-指令參考)
- [設定檔參考 (selftest.ini)](#設定檔參考)
- [AI 後端設定](#ai-後端設定)
- [靜態規則系統](#靜態規則系統)
- [AI Prompt 自訂](#ai-prompt-自訂)
- [輸出目錄結構](#輸出目錄結構)
- [Dry-Run 模式](#dry-run-模式)
- [進階用法](#進階用法)

---

## 簡介

selftest 是一個 Python CLI 工具，專為韌體驗證團隊設計。它能：

1. **自動分析**腳本的分支、路徑、外部呼叫、隨機變數
2. **呼叫地端 AI** 產生完整的 pytest 測試碼
3. **執行測試**並計算覆蓋率
4. **產出報告**（Terminal 即時彩色 + HTML 可上傳 Jira）

核心原則：
- **不依賴雲端** — 所有 AI 呼叫走地端模型或公司平台
- **不汙染原始碼** — 所有產出集中在 `.selftest/` 隱藏目錄
- **不自動改原始碼** — 修正只提供建議，由工程師決定是否套用

---

## 架構總覽

```
selftest/                       # 主套件
├── cli.py                      # Click CLI 入口（7 個指令）
├── config.py                   # INI 設定載入 + 環境變數展開
├── models.py                   # 全部 dataclass 資料模型
│
├── analyzer/                   # ◆ AST 靜態分析引擎
│   ├── ast_analyzer.py         #   主協調器（整合下面三個模組）
│   ├── branch_extractor.py     #   分支/路徑數/外部呼叫提取
│   ├── import_resolver.py      #   import 分類（stdlib / mock / real）
│   └── random_detector.py      #   隨機變數偵測 + 邊界值推導
│
├── generator/                  # ◆ AI 測試碼產生器
│   ├── ai_client.py            #   多後端 AI 呼叫（local_llm / company_platform）
│   ├── prompt_builder.py       #   組裝 prompt（模板 + 分析結果 + 使用者規則）
│   ├── test_builder.py         #   解析 AI 回應 + 斷言品質驗證
│   ├── mock_factory.py         #   自動產生 mock fixtures
│   └── cache.py                #   AI 回應快取（SHA256 + TTL 30天）
│
├── runner/                     # ◆ 測試執行
│   ├── executor.py             #   呼叫 pytest 跑產生的測試
│   └── coverage.py             #   覆蓋率 JSON 解析
│
├── reporter/                   # ◆ 報告輸出
│   ├── terminal.py             #   Rich 彩色終端報告
│   └── html.py                 #   HTML 報告（含逐行覆蓋率標色）
│
├── fixer/                      # ◆ 修正建議
│   ├── patch_generator.py      #   從測試失敗產生 patch 建議
│   ├── interactive_apply.py    #   互動式套用（有備份）
│   └── roo_exporter.py         #   匯出 Roo Code 指令檔
│
├── rules/                      # ◆ 靜態規則
│   ├── engine.py               #   YAML 規則載入 + regex 檢查
│   └── default_rules.yaml      #   內建規則（6 條）
│
└── templates/                  # ◆ 模板
    ├── _base.md                #   AI prompt 基底模板
    └── report.html.j2          #   HTML 報告 Jinja2 模板
```

### 模組依賴關係

```
cli.py
 ├── config.py (載入 selftest.ini)
 ├── analyzer/
 │    └── ast_analyzer.py → branch_extractor + import_resolver + random_detector
 ├── rules/engine.py (靜態規則檢查)
 ├── generator/
 │    ├── prompt_builder.py (組裝 prompt ← 分析結果 + 使用者規則)
 │    ├── ai_client.py (呼叫 AI ← prompt)
 │    ├── test_builder.py (解析 + 驗證 AI 回應)
 │    ├── mock_factory.py (產生 mock 程式碼)
 │    └── cache.py (快取 AI 回應)
 ├── runner/executor.py (跑 pytest)
 └── reporter/ (terminal.py + html.py)
```

---

## Pipeline 流程

```
selftest run your_script.py -v
              │
              ▼
  ┌───────────────────────┐
  │  [1/4] AST 分析        │
  │  analyze_file()        │
  │  ├─ 提取函式、分支、路徑 │
  │  ├─ 分類 imports        │
  │  └─ 偵測隨機變數+邊界值  │
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  [2/4] 靜態規則檢查     │
  │  check_rules()         │
  │  ├─ 內建 YAML 規則      │
  │  └─ 自訂規則 (可選)     │
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  [3/4] AI 產生測試碼    │
  │  ├─ 組裝 prompt         │
  │  ├─ 查詢快取            │
  │  ├─ 呼叫地端 AI         │
  │  ├─ 解析回應 → 程式碼    │
  │  ├─ 驗證斷言品質         │
  │  └─ 注入 mock fixtures  │
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  [4/4] 執行 pytest     │
  │  ├─ 跑產生的測試碼      │
  │  └─ 收集覆蓋率          │
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  輸出                   │
  │  ├─ Terminal 彩色報告   │
  │  ├─ HTML 報告           │
  │  └─ Roo Code 指令檔    │
  │     (--roo 才產生)      │
  └───────────────────────┘
```

---

## 安裝

### 從 GitHub clone 安裝

```bash
git clone https://github.com/billchen-hub/selftest-tool.git
cd selftest-tool/selftest
pip install .
```

### 驗證安裝

```bash
selftest --help
```

### 可選：安裝 local_llm 後端支援

```bash
pip install "selftest[local_llm]"
```

> 如果只用公司 AI 平台（Nexus），不需要裝 openai 套件。

---

## 快速開始

### 1. 初始化專案

在你的腳本專案根目錄執行：

```bash
cd /path/to/your/project
selftest init
```

互動式精靈會引導你設定：
- 腳本目錄位置
- 共用 Lib 目錄
- 需要 mock 的模組（例如 `tester`）
- AI provider（`local_llm` 或 `company_platform`）

完成後產生 `selftest.ini` 和 `.selftest/` 目錄。

### 2. 分析腳本（可選，了解分析結果）

```bash
selftest analyze scripts/verify_fw.py
```

### 3. 執行完整測試流程

```bash
selftest run scripts/verify_fw.py -v
```

### 4. 沒有 AI 時，先驗證 pipeline

```bash
selftest run scripts/verify_fw.py --dry-run -v
```

Dry-run 模式會用 mock 回應取代 AI，跑完整流程但不需要真實的 AI endpoint。

---

## CLI 指令參考

### 全域選項

| 選項 | 說明 |
|------|------|
| `--config <path>` | 指定 selftest.ini 路徑（預設向上搜尋） |
| `-v` / `-vv` | 詳細輸出（-v 一般，-vv 除錯） |

### `selftest init`

互動式初始化，產生 `selftest.ini` + `.selftest/` 目錄 + `.gitignore`。

### `selftest analyze <file>`

僅執行 AST 分析，輸出函式、分支數、路徑數、外部呼叫、隨機變數。
結果存入 `.selftest/data/<name>.analysis.json`。

### `selftest run <target> [OPTIONS]`

執行完整 pipeline（分析 → 規則 → AI 產生 → pytest → 報告）。

| 選項 | 說明 |
|------|------|
| `--provider <name>` | 臨時覆蓋 AI provider |
| `--rules-only` | 只跑靜態規則，不呼叫 AI |
| `--dry-run` | 用 mock AI 回應走完整流程（不需要真實 AI） |
| `--no-cache` | 強制重新產生（跳過快取） |
| `--roo` | 額外產生 Roo Code 指令檔 |
| `--patch` | 產生 patch 檔 |
| `--summary` | 目錄級摘要報告（target 為目錄時） |

**target 可以是單一檔案或目錄：**

```bash
# 單一檔案
selftest run scripts/verify_fw.py -v

# 整個目錄
selftest run scripts/ --summary -v
```

### `selftest report <file>`

從已存的 `.selftest/data/` 重新產生報告（不重跑測試）。

### `selftest fix <file>`

互動式套用修正建議。會先備份原始碼到 `.selftest/backups/`。

### `selftest clean`

清理 `.selftest/` 下的暫存檔案（測試碼、報告、快取等）。

---

## 設定檔參考

檔案：專案根目錄的 `selftest.ini`

```ini
[general]
# 腳本目錄（逗號分隔多個）
source_dirs = scripts/

# 共用 Lib 目錄
lib_dirs = lib/

# 強制 mock 的模組（逗號分隔）
mock_modules = tester

# 絕不 mock 的模組（逗號分隔，可留空）
never_mock =

# 覆蓋率門檻 (%)
coverage_threshold = 80

[ai]
# AI provider: local_llm | company_platform
provider = local_llm

# prompt / response token 上限
max_prompt_tokens = 4000
max_response_tokens = 4000

[local_llm]
# OpenAI 相容 API（vLLM, Ollama 等）
endpoint = http://localhost:8080/v1
model = qwen-72b
api_key =
timeout = 120

[company_platform]
# 公司 AI 平台 (Nexus)
base_url = http://ainexus.phison.com:5155
api_key = ${NEXUS_API_KEY}
share_code = your-model-share-code
timeout = 120

[report]
html_dir = .selftest/reports/
keep_days = 30
```

> **環境變數展開**：設定值支援 `${VAR}` 或 `$VAR` 語法，會自動展開。
> 例如 `api_key = ${NEXUS_API_KEY}` 會讀取環境變數。

---

## AI 後端設定

### local_llm（推薦用於地端模型）

適用於：vLLM、Ollama、llama.cpp server、任何 OpenAI 相容 API。

```ini
[ai]
provider = local_llm

[local_llm]
endpoint = http://localhost:8080/v1
model = qwen-72b
api_key = not-needed
```

> 需要安裝 openai 套件：`pip install "selftest[local_llm]"`

### company_platform（公司 AI 平台 Nexus）

適用於：公司內部 AI 平台，帶 RAG 功能。

```ini
[ai]
provider = company_platform

[company_platform]
base_url = http://ainexus.phison.com:5155
api_key = your-api-key
share_code = your-model-code
timeout = 120
```

> 不需要額外安裝套件（只用 requests）。

### 切換 provider

```bash
# 用 ini 設定
[ai]
provider = local_llm

# 或命令列臨時覆蓋
selftest run script.py --provider company_platform
```

---

## 靜態規則系統

### 內建規則（default_rules.yaml）

| 規則 ID | 嚴重度 | 說明 |
|---------|--------|------|
| `no_bare_except` | error | 禁止 bare `except:`，應指定具體 exception |
| `no_pass_in_except` | warning | except 區塊不應只有 `pass` |
| `no_exit_call` | warning | 避免 `exit()` / `sys.exit()`，應 raise exception |
| `no_assert_true` | error | 禁止 `assert True`（無意義斷言） |
| `no_assert_is_not_none` | warning | 禁止 `assert x is not None`（太寬鬆） |
| `no_assert_isinstance` | warning | 禁止僅用 isinstance 斷言 |

### 自訂規則

在 `.selftest/rules/static/` 下建立 YAML 檔：

**custom.yaml** — 覆蓋或新增規則：
```yaml
rules:
  # 關閉某條內建規則
  - id: no_pass_in_except
    severity: disabled

  # 新增自訂規則
  - id: no_hardcoded_ip
    description: "禁止寫死 IP 位址"
    severity: warning
    match:
      pattern: '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
```

優先順序：custom > project default > builtin。

---

## AI Prompt 自訂

在 `.selftest/rules/prompts/` 下放 Markdown 檔，會自動附加到 AI prompt 中。

例如 `01_tester_sdk.md`：
```markdown
## Tester SDK 說明
- tester.send_cmd(cmd, device) 會回傳 Response 物件
- Response 有 .status (int) 和 .data (bytes) 屬性
- status == 0 表示成功，非零表示失敗
```

例如 `02_coding_style.md`：
```markdown
## 測試命名規則
- 測試函式名稱用 test_<function>_<scenario> 格式
- 例如: test_verify_firmware_version_success
```

> 檔案按檔名排序載入，建議用數字前綴控制順序。

---

## 輸出目錄結構

所有產出集中在 `.selftest/`，不汙染原始碼目錄：

```
.selftest/
├── tests/          # AI 產生的測試碼 (test__<name>.py)
├── mocks/          # Mock fixtures
├── reports/        # HTML 報告
├── coverage/       # 覆蓋率原始資料
├── data/           # 分析結果 + 測試結果 JSON
├── patches/        # Patch 建議
├── backups/        # selftest fix 的原始碼備份
├── roo/            # Roo Code 指令檔
├── rules/
│   ├── prompts/    # 使用者自訂 AI prompt (*.md)
│   └── static/     # 使用者自訂靜態規則 (*.yaml)
├── cache/          # AI 回應快取
└── logs/           # 執行日誌
```

> 在 `.gitignore` 加入 `.selftest/` 即可（`selftest init` 會自動處理）。

---

## Dry-Run 模式

當沒有可用的 AI endpoint 時，可以用 dry-run 模式驗證整條 pipeline：

```bash
selftest run scripts/verify_fw.py --dry-run -v
```

Dry-run 模式會：
1. 正常執行 AST 分析
2. 正常執行靜態規則檢查
3. **跳過 AI 呼叫**，改用根據分析結果自動產生的基礎測試碼
4. 正常執行 pytest
5. 正常產生報告

產生的測試碼包含：
- 每個函式的基本呼叫測試
- 自動 mock 外部依賴
- 基本的回傳值斷言

> Dry-run 產生的測試品質不如真實 AI，但足以驗證 pipeline 正常運作。

---

## 進階用法

### 批次跑整個目錄

```bash
selftest run scripts/ --summary -v
```

產生每個檔案的報告 + 一份目錄級摘要。

### 只跑靜態規則（不呼叫 AI）

```bash
selftest run scripts/verify_fw.py --rules-only
```

### 產生 Roo Code 指令檔

```bash
selftest run scripts/verify_fw.py --roo
```

產生的 `.selftest/roo/fix_<name>.md` 可以在 VS Code 中讓 Roo Code 直接引用。

### 跳過快取，強制重新產生

```bash
selftest run scripts/verify_fw.py --no-cache
```

### 互動式套用修正

```bash
selftest fix scripts/verify_fw.py
```

會顯示建議修改列表，可選擇全部套用、部分套用或取消。原始碼會自動備份。

### CI/CD 整合

```bash
# GitLab CI 範例
selftest-check:
  stage: test
  script:
    - pip install .
    - selftest run scripts/ --summary
  artifacts:
    paths:
      - .selftest/reports/*.html
```

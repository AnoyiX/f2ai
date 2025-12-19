# F2AI - 文件智能解析服务

这是一个基于 FastAPI 构建的文件处理与转换服务，旨在将各种格式的文件（文档、图片、音视频等）解析为 AI 易于理解的格式（文本、图片列表等）。

## 核心功能

服务提供一个统一的 API 接口，接收任意格式的文件，根据文件类型自动执行相应的处理逻辑：

- **Office 文档 (Doc/Docx/PPT/PPTX)**
  - 自动转换为 PDF 格式。
  - 将 PDF 进一步转换为图片列表。
  - 最终返回转换后的 PDF 地址和图片列表地址。

- **PDF 文档**
  - 直接保留原文件。
  - 将 PDF 转换为图片列表。
  - 返回原文件地址和图片列表地址。

- **Excel 文档 (XLS/XLSX)**
  - 将每个 Sheet 转换为 HTML 表格。
  - 自动清洗 HTML：去除所有 CSS 样式、Script 脚本及无关属性，仅保留表格数据和布局（`rowspan`/`colspan`）。
  - 返回清洗后的 HTML 文本内容。

- **文本与代码文件 (Txt/Md/Html/Code...)**
  - 自动识别编码并读取文件内容。
  - 返回纯文本内容。

- **多媒体文件 (Video/Audio)**
  - 不进行转换，直接存储并返回文件访问地址。

## 技术栈

- **Web 框架**: FastAPI
- **文档转换**: LibreOffice (soffice)
- **PDF 处理**: Poppler (pdf2image)
- **HTML 清洗**: BeautifulSoup4
- **容器化**: Docker

## 快速开始

### 1. 使用 Docker 运行 (推荐)

项目已完全容器化，支持一键部署，无需手动安装复杂的依赖（如 LibreOffice, Poppler）。

```bash
# 构建镜像
docker build -t f2ai:latest .

# 运行容器
docker run -d -p 8000:8000 --name f2ai f2ai:latest
```

### 2. 本地开发 (MacOS)

如果需要在本地开发，请确保安装了以下系统依赖：

```bash
# 安装系统依赖
brew install --cask libreoffice
brew install poppler

# 安装 Python 依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload
```

## API 接口

### 文件处理接口

- **URL**: `/api/process`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### 请求参数

| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | File | 是 | 需要上传的文件 |

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "file": {
            "url": "/static/upload/2023/10/01/example.docx",
            "size": 10240,
            "name": "example.docx",
            "md5": "e10adc3949ba59abbe56e057f20f883e",
            "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        "ai": {
            "text": null,
            "images": [
                "/static/convert/e10adc3949ba59abbe56e057f20f883e/1.jpg",
                "/static/convert/e10adc3949ba59abbe56e057f20f883e/2.jpg"
            ],
            "pdf": "/static/convert/e10adc3949ba59abbe56e057f20f883e/result.pdf",
            "video": null,
            "audio": null
        }
    }
}
```

## 目录结构

```text
.
├── main.py               # FastAPI 入口
├── requirements.txt      # Python 依赖
├── Dockerfile            # Docker 构建文件
├── utils/
│   ├── file_handler.py   # 文件上传与存储逻辑
│   └── converter.py      # 核心转换逻辑 (LibreOffice/PDF/Excel/HTML)
└── static/               # 静态文件存储 (Docker 卷挂载点)
    ├── upload/           # 原始上传文件
    └── convert/          # 转换后的中间产物
```

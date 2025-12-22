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


## 快速开始

### 1. 使用 Docker 运行 (推荐)

项目已完全容器化，支持一键部署，无需手动安装复杂的依赖（如 LibreOffice, Poppler, ImageMagick）。

```bash
# 构建镜像
docker build -t f2ai:latest .

# 运行容器 (可选: 设置 API Token)
docker run -d -p 8000:8000 -e API_TOKEN=your_secret_token --name f2ai f2ai:latest
```

### 2. 本地开发 (MacOS)

如果需要在本地开发，请确保安装了以下系统依赖：

```bash
# 安装系统依赖
brew install --cask libreoffice
brew install poppler imagemagick

# 安装 Python 依赖
pip install -r requirements.txt

# 启动服务
# 可选: export API_TOKEN=your_secret_token
uvicorn main:app --reload
```

## API 接口

### 文件处理接口

- **URL**: `/api/process`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### 请求参数

| 参数名 | 类型    | 必选 | 说明                                                   |
| :----- | :------ | :--- | :----------------------------------------------------- |
| `file` | File    | 是   | 需要上传的文件                                         |
| `imgW` | Integer | 否   | 图片最大宽度（像素），仅当原图尺寸超过该值时才会缩小。 |
| `imgH` | Integer | 否   | 图片最大高度（像素），仅当原图尺寸超过该值时才会缩小。 |

#### 请求头 (可选)

| 参数名        | 说明                                                               |
| :------------ | :----------------------------------------------------------------- |
| `X-API-Token` | API 认证 Token (如果服务端设置了 `API_TOKEN` 环境变量，则此项必填) |

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

# F2AI - 文件智能解析与向量服务

这是一个基于 FastAPI 构建的综合性 AI 辅助服务，旨在解决 AI 应用中的非结构化数据处理难题。它提供了一站式的文件解析能力和多模态向量化检索能力，帮助开发者快速构建 RAG（检索增强生成）应用或多模态知识库。

---

## 快速开始

### 1. 环境变量配置

在启动服务前，请根据需要配置以下环境变量。建议创建 `.env` 文件。

| 变量名           | 必填   | 默认值                                                   | 说明                                             |
| :--------------- | :----- | :------------------------------------------------------- | :----------------------------------------------- |
| `API_TOKEN`      | 否     | -                                                        | 接口访问鉴权 Token，设置后所有接口需携带 `token` |
| `ARK_API_KEY`    | **是** | -                                                        | 火山引擎 API Key                                 |
| `ALI_API_KEY`    | 否     | -                                                        | 阿里云 API Key                                   |
| `QDRANT_HOST`    | 否     | `http://localhost:6333`                                  | Qdrant 向量数据库地址                            |
| `QDRANT_API_KEY` | 否     | -                                                        | Qdrant 访问密钥                                  |
| `POSTGRES_URL`   | 否     | `postgresql://postgres:postgres@localhost:5432/postgres` | PostgreSQL 数据库连接地址。                      |

### 2. 使用 Docker 运行 (推荐)

项目已完全容器化，无需手动安装复杂的系统依赖 (LibreOffice, Poppler, FFmpeg 等)。

```bash
# 构建镜像
docker build -t f2ai:latest .

# 运行容器 (示例包含向量服务配置)
docker run -d -p 8000:8000 \
  -v ~/static:/app/static \
  -e API_TOKEN=your_secret_token \
  -e ARK_API_KEY=your_ark_key \
  -e ALI_API_KEY=your_ali_key \
  -e QDRANT_HOST=http://host.docker.internal:6333 \
  --name f2ai f2ai:latest
```

### 3. 本地开发 (MacOS)

需安装必要的系统工具：

```bash
# 1. 安装系统依赖
brew install --cask libreoffice
brew install poppler imagemagick ffmpeg

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 启动服务
export ARK_API_KEY=your_key
uvicorn main:app --reload
```

---

## API 接口文档

所有接口均支持 `token` 鉴权。如果服务端设置了 `API_TOKEN`，则可以通过 Header `token: xxx` 参数传递。

### 1. 文件上传接口

仅上传文件，不进行任何解析处理。

- **URL**: `/api/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### 请求参数

| 参数名 | 类型 | 必选 | 默认值 | 说明                     |
| :----- | :--- | :--- | :----- | :----------------------- |
| `file` | File | 是   | -      | 需要上传的文件二进制流。 |

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "url": "/static/upload/2023/10/01/demo.pptx",
        "size": 10240,
        "name": "demo.pptx",
        "md5": "e10adc3949ba59abbe...",
        "contentType": "application/vnd.openxmlformats..."
    }
}
```

### 2. 文件解析接口

上传文件并进行智能化处理（转图片、提取文本、ASR 等）。

- **URL**: `/api/process`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### 请求参数

| 参数名          | 类型    | 必选 | 默认值 | 说明                               |
| :-------------- | :------ | :--- | :----- | :--------------------------------- |
| `file`          | File    | 是   | -      | 需要上传的文件二进制流。           |
| `imgW`          | Integer | 否   | 1024   | 图片最大宽度，超出会缩放。         |
| `imgH`          | Integer | 否   | 1024   | 图片最大高度，超出会缩放。         |
| `enbaleV2I`     | Boolean | 否   | True   | 是否开启视频抽帧转图片。           |
| `videoFPS`      | Float   | 否   | 1.0    | 视频截帧间隔（秒）。               |
| `enableA2T`     | Boolean | 否   | True   | 是否开启语音转文本。               |
| `audioLanguage` | String  | 否   | Auto   | 指定语音识别语言 (如 `zh`, `en`)。 |

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "file": {
            "url": "/static/upload/2023/10/01/demo.pptx",
            "size": 10240,
            "name": "demo.pptx",
            "md5": "e10adc3949ba59abbe...",
            "contentType": "application/vnd.openxmlformats..."
        },
        "ai": {
            "text": null,
            "images": [
                "/static/convert/e10adc.../1.jpg",
                "/static/convert/e10adc.../2.jpg"
            ],
            "pdf": "/static/convert/e10adc.../result.pdf",
            "video": null,
            "audio": null
        }
    }
}
```

### 3. 向量存储接口

将多模态数据（文本、图片、视频等）融合为一个向量并存储到 Qdrant，支持自定义元数据。
注意：此接口会将 `items` 列表中的所有内容压缩为一个向量存储。

- **URL**: `/api/vector/store`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型   | 必选 | 说明                                                             |
| :----------- | :----- | :--- | :--------------------------------------------------------------- |
| `collection` | String | 是   | 目标向量集合名称 (如 `ppt_knowledge`)。不存在会自动创建。        |
| `dbType`     | String | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。           |
| `aiModel`    | String | 否   | 向量化模型名称，默认 `doubao-embedding-vision-251215`。          |
| `items`      | List   | 是   | 需要向量化的多模态片段列表。                                     |
| `metadata`   | Object | 否   | 任意 JSON 对象，随向量存储 (如 `{"page": 1, "file": "a.pdf"}`)。 |

**Item 对象结构:**

| 字段        | 类型   | 必选 | 说明                                                     |
| :---------- | :----- | :--- | :------------------------------------------------------- |
| `type`      | String | 是   | `text` 或 `image_url`。                                  |
| `text`      | String | 否   | 当 type 为 text 时必填。                                 |
| `image_url` | Object | 否   | 当 type 为 image_url 时必填，格式 `{"url": "http..."}`。 |

#### 请求示例

```json
{
  "collection": "project_docs",
  "items": [
    {
      "type": "text",
      "text": "F2AI 是一个强大的文件处理服务。"
    },
    {
      "type": "image_url",
      "image_url": { "url": "https://example.com/diagram.jpg" }
    }
  ],
  "metadata": {
    "source": "readme.md",
    "section": "intro"
  }
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "id": "uuid-1..."
    }
}
```

### 4. 向量检索接口

输入多模态数据（文本、图片、视频等），在指定集合中检索最相似的内容。

- **URL**: `/api/vector/search`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型    | 必选 | 说明                                                   |
| :----------- | :------ | :--- | :----------------------------------------------------- |
| `collection` | String  | 是   | 搜索的目标集合名称。                                   |
| `dbType`     | String  | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。 |
| `aiModel`    | String  | 否   | 向量化模型名称，默认 `doubao-embedding-vision-251215`。|
| `items`      | List    | 是   | 查询对象列表，支持多模态混合查询。                     |
| `limit`      | Integer | 否   | 返回结果数量，默认 5。                                 |
| `offset`     | Integer | 否   | 结果偏移量，用于分页，默认 0。                         |
| `filter`     | Object  | 否   | 过滤条件，键值对匹配。                                 |
| `score`      | Float   | 否   | 相似度阈值，默认 0.2。                                 |

#### 请求示例

```json
{
  "collection": "project_docs",
  "items": [
    {
      "type": "text",
      "text": "文件处理服务的功能有哪些？"
    }
  ],
  "limit": 3,
  "filter": {
    "source": "readme.md"
  }
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "items": [
            {
                "id": "uuid-1...",
                "score": 0.892,
                "payload": {
                    "items": [
                        {
                            "type": "text",
                            "text": "F2AI 是一个强大的文件处理服务。"
                        },
                        {
                            "type": "image_url",
                            "image_url": { "url": "https://example.com/diagram.jpg" }
                        }
                    ],
                    "source": "readme.md",
                    "section": "intro"
                }
            }
        ]
    }
}
```

### 5. 向量元数据查询接口

根据元数据精确查询向量数据。

- **URL**: `/api/vector/query`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型    | 必选 | 说明                                                                                   |
| :----------- | :------ | :--- | :------------------------------------------------------------------------------------- |
| `collection` | String  | 是   | 搜索的目标集合名称。                                                                   |
| `dbType`     | String  | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。                                 |
| `query`      | Object  | 是   | 查询条件，键值对匹配。                                                                 |
| `limit`      | Integer | 否   | 返回结果数量，默认 5。                                                                 |
| `offset`     | Int/Str | 否   | 分页参数。传入整数时为偏移量（跳过 N 条）；传入字符串时为游标（上一页最后一条的 ID）。 |

#### 请求示例

```json
{
  "collection": "project_docs",
  "query": {
    "source": "readme.md"
  },
  "limit": 3
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "items": [
            {
                "id": "uuid-1...",
                "payload": {
                    "items": [
                        {
                            "type": "text",
                            "text": "F2AI 是一个强大的文件处理服务。"
                        }
                    ],
                    "source": "readme.md",
                    "section": "intro"
                }
            }
        ]
    }
}
```


### 6. 向量元数据修改接口

根据 filter 条件修改指定集合中向量的元数据。

- **URL**: `/api/vector/update`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型   | 必选 | 说明                                                            |
| :----------- | :----- | :--- | :-------------------------------------------------------------- |
| `collection` | String | 是   | 目标向量集合名称。                                              |
| `dbType`     | String | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。          |
| `filter`     | Object | 是   | 匹配条件，精确匹配 metadata 中的字段 (如 `{"file": "a.pdf"}`)。 |
| `payload`    | Object | 是   | 需要更新或添加的元数据。                                        |

#### 请求示例

```json
{
  "collection": "project_docs",
  "filter": {
    "file": "a.pdf"
  },
  "payload": {
    "status": "processed",
    "updated_at": "2023-10-01"
  }
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "updated": true
    }
}
```


### 7. 向量删除接口

根据 filter 条件删除指定集合中的向量。

- **URL**: `/api/vector/delete`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型   | 必选 | 说明                                                            |
| :----------- | :----- | :--- | :-------------------------------------------------------------- |
| `collection` | String | 是   | 目标向量集合名称。                                              |
| `dbType`     | String | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。          |
| `filter`     | Object | 是   | 删除条件，精确匹配 metadata 中的字段 (如 `{"file": "a.pdf"}`)。 |

#### 请求示例

```json
{
  "collection": "project_docs",
  "filter": {
    "file": "a.pdf"
  }
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "deleted": true
    }
}
```

### 8. 向量清空接口

清空指定集合中的所有向量数据。

- **URL**: `/api/vector/clear`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (JSON Body)

| 参数名       | 类型   | 必选 | 说明                                                   |
| :----------- | :----- | :--- | :----------------------------------------------------- |
| `collection` | String | 是   | 需要清空的集合名称。                                   |
| `dbType`     | String | 否   | 向量数据库类型，可选 `qdrant` (默认) 或 `postgresql`。 |

#### 请求示例

```json
{
  "collection": "project_docs"
}
```

#### 响应示例

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "deleted": true
    }
}
```

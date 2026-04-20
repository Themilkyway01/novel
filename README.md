# 小说推荐系统

基于 Django + Vue 3 的个性化小说推荐平台，使用 SVD 协同过滤算法提供精准推荐。

## 功能特性

- **用户认证**：注册、登录、个人信息管理
- **小说浏览**：分类查看、搜索、详情页
- **智能推荐**：热门推荐、最新更新、个性化推荐、冷启动推荐
- **相似推荐**：基于内容相似度和阅读历史的推荐
- **用户行为**：阅读记录、评分、偏好设置

## 技术栈

### 后端
- **框架**：Django 4.2 + Django REST Framework
- **数据库**：MySQL / SQLite
- **缓存**：Redis + Django Redis
- **推荐算法**：Surprise (SVD) + TF-IDF + 混合推荐策略
- **分词工具**：jieba

### 前端
- **框架**：Vue 3 + Vite
- **UI 组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP 客户端**：Axios

## 项目结构

```
d:/novel/
├── README.md                    # 项目说明文档
├── start_server.bat             # Windows 一键启动脚本
├── stop-all.bat                 # Windows 一键停止脚本
├── .gitignore                   # Git 忽略配置
│
├── data_processing/             # 数据处理模块
│   └── novel_process.py         # 数据清洗与合并脚本
│
├── data_scraping/               # 数据采集模块
│   ├── novel/                   # 小说爬虫
│   │   ├── boy.py              # 起点男频小说爬虫
│   │   ├── girl.py             # 起点女频小说爬虫
│   │   ├── publish.py          # 出版图书爬虫
│   │   └── *.json              # 分类配置和爬取进度
│   └── user/                    # 用户数据
│       ├── simulation.py       # 用户行为模拟脚本
│       └── validation.py       # 数据验证脚本
│
├── model_building/              # 模型训练模块
│   ├── main.py                 # 模型训练入口
│   ├── recommender.py          # 核心算法实现
│   ├── api.py                  # 模型 API 封装
│   ├── svd_model.pkl           # 训练好的 SVD 模型
│   ├── tfidf.pkl               # 训练好的 TF-IDF 模型
│   ├── svd_tuning_report.json  # SVD 模型调优报告
│   └── svd_factors_vs_ndcg.png # 调优可视化图
│
├── web_backend/                 # 后端服务（Django REST API）
│   ├── api/                    # Django 应用目录
│   │   ├── migrations/         # 数据库迁移文件
│   │   ├── models.py           # 数据模型定义
│   │   ├── serializers.py      # DRF 序列化器
│   │   ├── urls.py             # URL 路由配置
│   │   ├── views/              # 视图模块
│   │   │   ├── auth.py        # 认证相关视图
│   │   │   ├── behaviors.py   # 用户行为视图
│   │   │   ├── novels.py      # 小说相关视图
│   │   │   └── recommendations.py  # 推荐相关视图
│   │   └── recommender/        # 推荐引擎模块
│   │       ├── base.py         # 基础推荐引擎单例
│   │       ├── collaborative.py # 协同过滤算法
│   │       ├── content.py      # 内容推荐算法
│   │       ├── diversity.py    # 多样性推荐算法
│   │       └── sampling.py     # 采样策略
│   ├── models/                 # 预训练模型文件
│   │   ├── svd_model.pkl
│   │   └── tfidf.pkl
│   ├── novel_recommender/      # Django 项目配置
│   │   ├── settings.py        # 配置文件
│   │   ├── urls.py            # 根 URL 配置
│   │   └── wsgi.py            # WSGI 应用配置
│   ├── requirements.txt        # Python 依赖包列表
│   ├── init_db.sql            # 数据库初始化脚本
│   └── manage.py              # Django 命令行工具
│
└── web_frontend/               # 前端界面（Vue 3 SPA）
    ├── src/                    # Vue 源代码
    │   ├── api/               # API 调用封装
    │   │   └── index.js
    │   ├── components/        # 可复用组件
    │   │   └── NovelCard.vue  # 小说卡片组件
    │   ├── router/            # 路由配置
    │   │   └── index.js
    │   ├── stores/            # Pinia 状态管理
    │   │   └── user.js        # 用户状态管理
    │   ├── utils/             # 工具函数
    │   │   └── request.js     # Axios 封装
    │   └── views/             # 页面视图
    │       ├── Home.vue              # 首页
    │       ├── Login.vue             # 登录页
    │       ├── Register.vue          # 注册页
    │       ├── Profile.vue           # 个人资料页
    │       ├── Category.vue          # 分类浏览页
    │       ├── NovelDetail.vue       # 小说详情页
    │       ├── Rank.vue              # 排行榜页
    │       ├── RecommendView.vue     # 推荐页面
    │       ├── ColdStartView.vue     # 冷启动页面
    │       └── History.vue           # 阅读历史页
    ├── dist/                  # 构建输出目录
    ├── index.html             # 主 HTML 文件
    ├── package.json           # NPM 配置
    ├── package-lock.json      # 依赖锁定文件
    └── vite.config.js         # Vite 构建配置
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+（推荐）或 SQLite
- Redis 6.0+
- Git（用于版本控制）

### 1. 克隆项目

```bash
git clone <项目地址>
cd novel
```

### 2. 后端环境配置

#### 安装 Python 依赖

```bash
cd web_backend
pip install -r requirements.txt
```

#### 数据库配置

1. **MySQL 配置**（推荐）：
   - 创建数据库：`create database novel_data;`
   - 修改 `web_backend/novel_recommender/settings.py` 中的数据库配置：
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'novel_data',
             'USER': 'root',
             'PASSWORD': 'your_password',
             'HOST': 'localhost',
             'PORT': '3306',
         }
     }
     ```

2. **SQLite 配置**（开发用）：
   - 使用默认 SQLite 配置，无需修改。

#### 数据库初始化

```bash
# 执行数据库迁移
python manage.py migrate

# 执行初始化脚本（可选，用于创建测试数据）
mysql -u root -p novel_data < init_db.sql
```

#### 启动 Redis 服务

```bash
# Windows：下载并运行 Redis，或使用 WSL
# Linux/macOS：
redis-server
```

#### 启动 Django 后端

```bash
python manage.py runserver
```

后端服务地址：http://localhost:8000

### 3. 前端环境配置

```bash
cd ../web_frontend
npm install
npm run dev
```

前端服务地址：http://localhost:5173

### 4. 一键启动（Windows）

项目提供了 Windows 批处理脚本简化启动流程：

```bash
# 启动所有服务（Redis、Django、Vue）
start_server.bat

# 停止所有服务
stop-all.bat
```

## 数据管道

### 1. 数据爬取

系统从起点中文网爬取小说数据：

```bash
cd data_scraping/novel
# 爬取男频小说
python boy.py
# 爬取女频小说
python girl.py
# 爬取出版图书
python publish.py
```

### 2. 数据处理

```bash
cd ../data_processing
python novel_process.py
```

### 3. 模型训练

```bash
cd ../model_building
python main.py
```

## API 接口

### 认证相关

| 接口 | 方法 | 说明 | 请求参数 |
|------|------|------|----------|
| `/api/auth/login/` | POST | 用户登录 | `username`, `password` |
| `/api/auth/register/` | POST | 用户注册 | `username`, `password`, `email` |
| `/api/auth/profile/` | GET | 获取用户信息 | 需要认证 |
| `/api/auth/profile/update/` | POST | 更新用户信息 | 需要认证，`nickname`, `avatar` 等 |

### 小说相关

| 接口 | 方法 | 说明 | 请求参数 |
|------|------|------|----------|
| `/api/novels/` | GET | 小说列表 | `page`, `page_size`, `category`, `keyword` |
| `/api/novels/<id>/` | GET | 小说详情 | 路径参数：小说 ID |
| `/api/novels/categories/` | GET | 获取分类列表 | 无 |
| `/api/novels/<id>/similar/` | GET | 相似小说 | 路径参数：小说 ID |

### 推荐相关

| 接口 | 方法 | 说明 | 请求参数 |
|------|------|------|----------|
| `/api/hot/` | GET | 热门推荐 | `limit`（默认 10） |
| `/api/recent/` | GET | 最新更新 | `limit`（默认 10） |
| `/api/recommend/personal/` | GET | 个性化推荐 | 需要认证，`limit`（默认 20） |
| `/api/recommend/` | GET | 通用推荐 | `limit`（默认 20），`category`（可选） |

### 用户行为

| 接口 | 方法 | 说明 | 请求参数 |
|------|------|------|----------|
| `/api/ratings/` | POST | 提交评分 | 需要认证，`novel_id`, `rating`（1-5） |
| `/api/user/history/` | GET | 阅读历史 | 需要认证，`page`, `page_size` |
| `/api/user/read/` | POST | 记录阅读行为 | 需要认证，`novel_id`, `duration` |

## 推荐算法详解

### 混合推荐策略

系统采用多种推荐算法融合的策略，以平衡精度、多样性和冷启动问题：

#### 1. 协同过滤（SVD 矩阵分解）
- **算法**：使用 Surprise 库的 SVD 算法
- **输入**：用户-物品评分矩阵（显式+隐式反馈）
- **输出**：用户对未读小说的预测评分
- **模型**：`svd_model.pkl`，150 个隐因子，NDCG@5 为 0.4219

#### 2. 内容相似度（TF-IDF + 余弦相似度）
- **算法**：基于小说简介和标签的 TF-IDF 向量化
- **分词**：使用 jieba 进行中文分词
- **输出**：小说间的文本相似度矩阵
- **模型**：`tfidf.pkl`，支持增量学习

#### 3. 多样性推荐
- **策略**：基于信息熵的多类别平衡
- **目标**：避免信息茧房，推荐跨类别小说
- **实现**：`recommender/diversity.py` 中的多样性采样算法

#### 4. 冷启动策略
- **新用户**：基于热门推荐 + 最新更新 + 随机探索
- **新小说**：基于内容相似度推荐给相关读者

#### 5. 混合加权
最终推荐分数 = 0.6 × 协同过滤分数 + 0.3 × 内容相似度分数 + 0.1 × 多样性因子

### 用户画像系统
- **阅读偏好**：基于阅读历史计算分类偏好权重
- **活跃度**：基于阅读频率和时长
- **兴趣演化**：基于时间衰减的权重调整

## 管理命令

### Django 内置命令
```bash
# 创建超级用户
python manage.py createsuperuser

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 清理缓存
python manage.py clear_cache

# 启动开发服务器
python manage.py runserver 0.0.0.0:8000
```

### 自定义命令
```bash
# 训练推荐模型
python manage.py train_model

# 更新推荐缓存
python manage.py refresh_recommendations

# 导入测试数据
python manage.py import_test_data
```

## 开发指南

### 代码规范

- **Python**：遵循 PEP 8，使用 Black 格式化
- **JavaScript/Vue**：遵循 ESLint 规则，使用 Prettier 格式化
- **Git 提交**：使用语义化提交格式（feat:, fix:, docs:, style:, refactor:, test:, chore:）

### 分支管理

- `master`：主分支，稳定版本
- `develop`：开发分支，集成新功能
- `feature/*`：功能分支，开发新功能
- `bugfix/*`：修复分支，修复 bug
- `release/*`：发布分支，版本发布

### 项目配置说明

#### 后端配置（settings.py）
- **数据库**：支持 MySQL 和 SQLite
- **缓存**：Redis 用于缓存推荐结果
- **CORS**：配置前端域名白名单
- **JWT**：使用 JWT 进行用户认证
- **日志**：分级日志配置，便于调试

#### 前端配置（vite.config.js）
- **代理**：开发环境代理 API 请求到后端
- **打包**：支持代码分割和懒加载
- **兼容性**：支持现代浏览器

### 扩展建议

1. **增加推荐算法**：在 `recommender/` 目录下添加新的算法模块
2. **增加数据源**：在 `data_scraping/` 目录下添加新的爬虫脚本
3. **优化前端交互**：在 `web_frontend/src/` 目录下添加新组件
4. **增加数据分析**：在 `model_building/` 目录下添加分析脚本

## 性能优化

### 缓存策略
- 热门推荐结果缓存：10 分钟
- 用户个性化推荐缓存：5 分钟
- 小说详情缓存：30 分钟
 (使用 Redis 作为缓存后端)

### 数据库优化
- 为常用查询字段添加索引
- 使用分页限制查询结果数量
- 定期清理历史数据

### 前端优化
- 图片懒加载
- 组件按需加载
- API 请求节流

## 常见问题

### Q1: 数据库连接失败
**A**：检查 MySQL 服务是否启动，数据库配置是否正确。

### Q2: Redis 连接失败
**A**：检查 Redis 服务是否启动，配置端口是否为默认 6379。

### Q3: 前端无法访问后端 API
**A**：检查 CORS 配置，确保前端域名在允许列表中。

### Q4: 推荐结果不准确
**A**：尝试重新训练模型，或调整混合权重参数。

### Q5: 爬虫被网站屏蔽
**A**：调整爬虫频率，添加 User-Agent 头，或使用代理 IP。

## 许可证

MIT License

## 联系方式

- 项目问题请提交 Issue
- 技术讨论欢迎 Pull Request
- 邮箱：待补充

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
- **推荐算法**：Surprise (SVD) + TF-IDF

### 前端
- **框架**：Vue 3 + Vite
- **UI**：自定义组件
- **状态管理**：Pinia
- **路由**：Vue Router

## 项目结构

```
d:/novel/
├── web_backend/              # Django 后端
│   ├── api/                  # API 应用
│   │   ├── models.py         # 数据模型
│   │   ├── serializers.py    # 序列化器
│   │   ├── urls.py           # URL 配置
│   │   ├── recommender/      # 推荐引擎模块
│   │   │   ├── base.py       # 核心推荐逻辑
│   │   │   ├── collaborative.py
│   │   │   ├── content.py
│   │   │   ├── diversity.py
│   │   │   └── sampling.py
│   │   └── views/            # 视图模块
│   │       ├── auth.py       # 认证相关
│   │       ├── novels.py      # 小说相关
│   │       ├── recommendations.py  # 推荐相关
│   │       └── behaviors.py   # 用户行为
│   ├── models/               # 模型文件
│   │   ├── svd_model.pkl
│   │   └── tfidf.pkl
│   └── novel_recommender/     # Django 项目配置
│
├── web_frontend/             # Vue 前端
│   └── src/
│       ├── api/              # API 调用
│       ├── components/       # 公共组件
│       ├── views/            # 页面视图
│       ├── stores/           # 状态管理
│       └── router/          # 路由配置
│
├── model_building/            # 模型训练脚本
├── data_processing/          # 数据处理脚本
├── data_scraping/            # 数据爬取脚本
└── 推荐系统实现说明.md        # 技术文档
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+ / SQLite
- Redis 6.0+

### 后端启动

```bash
cd d:/novel/web_backend

# 安装依赖
pip install -r requirements.txt

# 配置数据库（编辑 settings.py）

# 数据库迁移
python manage.py migrate

# 启动服务
python manage.py runserver
```

服务地址：http://localhost:8000

### 前端启动

```bash
cd d:/novel/web_frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

前端地址：http://localhost:5173

## API 接口

### 认证相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login/` | POST | 用户登录 |
| `/api/auth/register/` | POST | 用户注册 |
| `/api/auth/profile/` | GET | 获取用户信息 |
| `/api/auth/profile/update/` | POST | 更新用户信息 |

### 小说相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/novels/` | GET | 小说列表 |
| `/api/novels/<id>/` | GET | 小说详情 |
| `/api/novels/categories/` | GET | 获取分类列表 |
| `/api/novels/<id>/similar/` | GET | 相似小说 |

### 推荐相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/hot/` | GET | 热门推荐 |
| `/api/recent/` | GET | 最新更新 |
| `/api/recommend/personal/` | GET | 个性化推荐 |
| `/api/recommend/` | GET | 通用推荐 |

### 用户行为

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/ratings/` | POST | 提交评分 |
| `/api/user/history/` | GET | 阅读历史 |

## 推荐算法

系统采用混合推荐策略：

1. **协同过滤**：基于 SVD 矩阵分解的用户-物品评分预测
2. **内容相似度**：基于 TF-IDF 的文本相似度计算
3. **多样性因子**：避免信息茧房，引入跨分类推荐

## 管理命令

```bash
# 清理缓存
python manage.py clear_cache

# 创建超级用户
python manage.py createsuperuser
```

## 开发指南

### 代码规范

- Python：遵循 PEP 8
- JavaScript：遵循 ESLint 规则
- Git 提交信息：使用语义化提交格式

### 分支管理

- `main`：主分支，稳定版本
- `develop`：开发分支
- `feature/*`：功能分支

## 许可证

MIT License

## 联系方式

项目问题请提交 Issue

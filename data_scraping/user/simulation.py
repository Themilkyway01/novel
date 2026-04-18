"""
模拟用户交互数据
基于 novel_info 表生成
"""
import numpy as np
import pandas as pd
import random
from sqlalchemy import create_engine, text
from tqdm import tqdm

# ------------------------ 1.配置 ------------------------
# 模拟参数
NUM_USERS = 5000                # 用户数
COLD_START_USER_RATIO = 0.05    # 冷启动用户占比（交互极少）
COLD_START_ITEM_RATIO = 0.05    # 冷启动物品占比（无人交互）
MIN_READ_TIME = 10              # 最短阅读时长（分钟）
MAX_READ_TIME = 14400           # 最长阅读时长（分钟）
READING_SPEED = 400             # 阅读速度
HOTNESS_WEIGHT = 0.3            # 热度影响系数（0~1），0表示完全基于偏好，1表示完全基于热度
RANDOM_SEED = 42                # 随机种子，保证可复现

# ----------------------- 2.初始化 -----------------------
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# 数据库引擎
engine = create_engine('mysql+pymysql://root:123456@localhost/novel_data?charset=utf8mb4')
# 读取小说信息
df_novel = pd.read_sql('SELECT * FROM novel_info', engine)
df_novel = df_novel.reset_index()
print('总小说:', df_novel.shape)

# -------------------- 3.构建映射关系 ---------------------
# 根据书籍数量进行加权
cate_counts = df_novel['cate'].value_counts()
cate_weights = [cate_counts.get(0, 0), cate_counts.get(1, 0), cate_counts.get(2, 0)]
if sum(cate_weights) > 0:
    cate_probs = np.array(cate_weights) / np.sum(cate_weights)
else:
    cate_probs = [1/3, 1/3, 1/3]
print('男频\女频\出版三者权重:', cate_probs)

# cate --> category
cate_to_cats = {}
# category --> sub_category
cats_to_subcats = {}
# category --> author
cats_to_authors = {}

for cate_val in [0, 1, 2]:
    df_cate = df_novel[df_novel['cate'] == cate_val]
    # 分类
    categories = df_cate['category'].unique().tolist()
    cate_to_cats[cate_val] = categories
    for cat in categories:
        # 子分类
        subcats = df_cate[df_cate['category'] == cat]['sub_category'].unique().tolist()
        cats_to_subcats[cat] = subcats
        # 作者
        authors = df_cate[df_cate['category'] == cat]['author'].unique().tolist()
        cats_to_authors[cat] = authors

# 打印统计信息
print('女频(0)分类数:', len(cate_to_cats.get(0, [])))
print('男频(1)分类数:', len(cate_to_cats.get(1, [])))
print('出版(2)分类数:', len(cate_to_cats.get(2, [])))

# -------------------- 4.生成用户档案 ---------------------
print('生成用户档案...')
user_profiles = []
for uid in range(NUM_USERS):
    # 加权选择一个cate
    liked_cate = np.random.choice([0, 1, 2], p=cate_probs)
    # 获取该cate下的所有分类
    avail_categories = cate_to_cats.get(liked_cate, [])
    # 随机选择 1-3 个分类
    num_cats = np.random.randint(1, 4)
    liked_cats = list(np.random.choice(avail_categories, size=num_cats, replace=False))

    # 收集这些分类下的所有子分类
    all_subcats = []
    for cat in liked_cats:
        all_subcats.extend(cats_to_subcats.get(cat, []))
    all_subcats = list(set(all_subcats))
    num_subcats = np.random.randint(1, min(4, len(all_subcats) + 1))
    liked_subcats = list(np.random.choice(all_subcats, size=num_subcats, replace=False)) if all_subcats else []

    # 收集这些分类下的所有作者
    all_authors = []
    for cat in liked_cats:
        all_authors.extend(cats_to_authors.get(cat, []))
    all_authors = list(set(all_authors))
    num_authors = np.random.randint(0, min(3, len(all_authors) + 1))
    liked_authors = list(np.random.choice(all_authors, size=num_authors, replace=False)) if all_authors else []

    # 活跃度（交互数量）
    if np.random.random() < COLD_START_USER_RATIO:
        activity = np.random.randint(1, 4)
    else:
        activity = int(np.random.exponential(scale=30)) + 5
        activity = min(activity, 200)

    user_profiles.append({
        'user_id': uid,
        'liked_cate': int(liked_cate),
        'liked_cats': liked_cats,
        'liked_subcats': liked_subcats,
        'liked_authors': liked_authors,
        'activity': activity,
        'cold_start': (activity <= 3)
    })

# ------------ 5.准备候选物品池（排除冷启动物品） ------------
print('准备物品池...')
# 按总推荐数升序排序，取前 COLD_START_ITEM_RATIO 的物品作为冷启动物品
df_sorted = df_novel.sort_values('all_recommend')
cold_item_count = int(COLD_START_ITEM_RATIO * len(df_sorted))
cold_item_ids = set(df_sorted.head(cold_item_count)['index'].tolist())
print('冷启动物品数:', len(cold_item_ids), f'占 {len(cold_item_ids) / len(df_novel):.1%}')

# 非冷启动物品列表
hot_items = df_novel[~df_novel['index'].isin(cold_item_ids)].to_dict('records')
print('可交互物品数:', len(hot_items))

# 热度值总和（用于归一化）
max_recommend = df_novel['all_recommend'].max()
print('热度值总和:', max_recommend)

# --------------------- 6.定义权重函数 ---------------------
def compute_match_score(profile, book):
    score = 0.1
    if book['cate'] == profile['liked_cate']:
        score += 0.2
    if book['category'] in profile['liked_cats']:
        score += 0.3
    if book['sub_category'] in profile['liked_subcats']:
        score += 0.2
    if book['author'] in profile['liked_authors']:
        score += 0.2
    return min(score, 1.0)

def compute_popularity(all_recommend):
    # 归一化
    return np.log1p(all_recommend) / np.log1p(max_recommend)

# ------------------- 7.阅读时长生成函数 -------------------
def generate_read_time(book, match_score, popularity):
    # 估算基础阅读时间
    base_time = book['wordcount'] / READING_SPEED
    match_factor = 0.5 + match_score * 1.5              # 匹配度影响 [0.5, 2.0] ，用户越喜欢，读得越完整（时间越长）
    popularity_factor = 0.8 + popularity * 0.4          # 热度影响 [0.8, 1.2] ，热门书可能更易读完，但也可正向影响
    noise = np.random.lognormal(mean=0, sigma=0.3)      # 随机噪声（对数正态分布）
    # 总时间
    total_time = base_time * match_factor * popularity_factor * noise
    # 限制范围并取整
    return int(round(np.clip(total_time, MIN_READ_TIME, MAX_READ_TIME)))

# ------------------- 8.生成交互记录 -------------------
print('生成用户行为记录...')
# 存储 (user_id, novel_id, read_time, timestamp)
interactions = []
for profile in tqdm(user_profiles, desc='处理用户'):
    user_id = profile['user_id']
    user_cate = profile['liked_cate']
    activity = profile['activity']
    # 偏好加权抽取
    # 计算每个候选物品的匹配得分
    scores = [compute_match_score(profile, book) for book in hot_items]
    popularises = [compute_popularity(book['all_recommend']) for book in hot_items]
    # 混合权重
    weights = (1 - HOTNESS_WEIGHT) * np.array(scores) + HOTNESS_WEIGHT * np.array(popularises)
    # 归一化
    weights = weights / np.sum(weights)
    # 不放回抽样，选择 activity 个物品
    selected_indices = np.random.choice(len(weights), size=activity, replace=False, p=weights)
    selected_books = [hot_items[i] for i in selected_indices]

    # 为选中的每本书生成总阅读时长和随机时间戳
    for book in selected_books:
        match_score = compute_match_score(profile, book)
        popularity = compute_popularity(book['all_recommend'])
        read_time = generate_read_time(book, match_score, popularity)
        timestamp = pd.Timestamp.now() - pd.Timedelta(days=random.randint(1, 365))
        interactions.append((user_id, user_cate, book['index'], read_time, timestamp))

print('总交互记录数:', {len(interactions)})
df_behavior = pd.DataFrame(interactions, columns=['user_id', 'user_cate', 'novel_id', 'read_time', 'timestamp'])

# ------------------- 9.补充低交互物品 -------------------
# 确保非冷启动物品至少有 10 次交互，避免数据过于稀疏
# print('检查物品交互次数...')
# item_counts = df_behavior['novel_id'].value_counts()
# low_inter_items = item_counts[item_counts < 10].index.tolist()
# if low_inter_items:
#     print(f'发现 {len(low_inter_items)} 个物品交互次数少于10，正在补充...')
#     supplement = []
#     for item_id in low_inter_items:
#         book = df_novel[df_novel['index'] == item_id].iloc[0]
#         needed = 10 - item_counts[item_id]      # 需要补充的交互数
#         available_users = [p['user_id'] for p in user_profiles]     # 所有用户ID
#         chosen_users = np.random.choice(available_users, size=needed, replace=False)
#         for uid in chosen_users:
#             profile = next(p for p in user_profiles if p['user_id'] == uid)
#             match_score = compute_match_score(profile, book.to_dict())
#             popularity = compute_popularity(book['all_recommend'])
#             read_time = generate_read_time(book, match_score, popularity)
#             timestamp = pd.Timestamp.now() - pd.Timedelta(days=random.randint(1, 365))
#             supplement.append((uid, book['index'], read_time, timestamp))
#     df_supp = pd.DataFrame(supplement, columns=['user_id', 'novel_id', 'read_time', 'timestamp'])
#     df_behavior = pd.concat([df_behavior, df_supp], ignore_index=True)
#     print('补充后总记录:', len(df_behavior))

# ------------------- 10.存储数据库 -------------------
print('正在写入数据库...')
create_table_sql = """
CREATE TABLE IF NOT EXISTS user_behavior (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    user_cate SMALLINT NOT NULL COMMENT '用户Cate',
    novel_id INT NOT NULL COMMENT '小说ID',
    read_time SMALLINT NOT NULL CHECK (read_time BETWEEN 10 AND 14400) COMMENT '总阅读时长',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id), 
    INDEX idx_cate (user_cate), 
    INDEX idx_item (novel_id)
);
"""
with engine.connect() as conn:
    conn.execute(text(create_table_sql))

df_behavior.to_sql('user_behavior', con=engine, index=False, if_exists='replace')
print('用户行为数据已写入 user_behavior 表')

# ------------------- 11.数据统计验证 -------------------
print("\n=== 数据统计验证 ===")
print("阅读时长分布:")
print(df_behavior['read_time'].describe())
print("\n每个用户的阅读数量分布:")
user_counts = df_behavior.groupby('user_id').size()
print(user_counts.describe())
print("\n每本书的阅读人数分布:")
item_counts = df_behavior.groupby('novel_id').size()
print(item_counts.describe())

# 冷启动用户统计
cold_users = [p['user_id'] for p in user_profiles if p['cold_start']]
cold_user_records = df_behavior[df_behavior['user_id'].isin(cold_users)]
print(f"\n冷启动用户数: {len(cold_users)}，平均阅读数: {cold_user_records.groupby('user_id').size().mean():.1f}")

# 各 cate 的用户数分布（检查加权效果）
cate_user_counts = {0:0, 1:0, 2:0}
for p in user_profiles:
    cate_user_counts[p['liked_cate']] += 1
print(f"\n各 cate 用户数: {cate_user_counts}")

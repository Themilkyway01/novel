"""
数据处理
"""
import pandas as pd
from sqlalchemy import create_engine    # 用于将DataFrame快速写入MySQL
from sqlalchemy import types

# 创建数据库连接（sqlalchemy）
engine = create_engine('mysql+pymysql://root:123456@localhost/novel_data?charset=utf8mb4')

# 设置输出行宽（适中，铺满一行）
LINE_WIDTH = 80

# ------------------------- 1. 读取三张表 -------------------------
df_boy = pd.read_sql('SELECT * FROM boy_novel;', engine)
df_girl = pd.read_sql('SELECT * FROM girl_novel;', engine)
df_publish = pd.read_sql('SELECT * FROM publish_book;', engine)

print('男生小说:', df_boy.shape)
print('女生小说:', df_girl.shape)
print('出版图书:', df_publish.shape)
print('-' * LINE_WIDTH)
print()

# ------------------------- 2. 统一字段结构 ------------------------
print('男生表字段:', df_boy.columns.tolist())
print('女生表字段:', df_girl.columns.tolist())
print('出版表字段:', df_publish.columns.tolist())
print('-' * LINE_WIDTH)
print()

# 为出版表添加缺失字段，并赋予合理默认值
df_publish['up_status'] = '完本'
df_publish['signed'] = '签约'
df_publish['vip'] = 'VIP'
df_publish['sub_category'] = '出版'

# 合并后区分男生(1)、女生(0)、出版(2)
df_boy['cate'] = 1
df_girl['cate'] = 0
df_publish['cate'] = 2

# 统一字段顺序
common_columns = [
    'cate', 'img', 'name', 'author', 'up_time', 'up_chapter', 'up_status', 'signed', 'vip', 'category',
    'sub_category', 'wordcount', 'all_recommend', 'week_recommend', 'introduction', 'chapters'
]
df_boy = df_boy[common_columns]
df_girl = df_girl[common_columns]
df_publish = df_publish[common_columns]

# 合并三个表
df_all = pd.concat([df_boy, df_girl, df_publish], ignore_index=True)
print('合并后:', df_all.shape)
print('-' * LINE_WIDTH)
print()

# 日期字段统一格式
df_all['up_time'] = pd.to_datetime(df_all['up_time'])

# 更新状态、签约状态、是否VIP 三个字段统一为01编码类
df_all['up_status'] = df_all['up_status'].map({'连载': 0, '完本': 1})
df_all['signed'] = df_all['signed'].map({'未签约': 0, '签约': 1})
df_all['vip'] = df_all['vip'].map({'免费': 0, 'VIP': 1})

# -------------------------- 3. 数据清洗 -------------------------
# 查看缺失情况
print(df_all.isnull().sum())
print('-' * LINE_WIDTH)
print()

# 查看异常情况
print(df_all[
    (df_all['wordcount'] >= 0) &
    (df_all['all_recommend'] >= 0) &
    (df_all['week_recommend'] >= 0)
].shape)

# 重复值处理
df_all = df_all.drop_duplicates(subset=common_columns, keep='first')
print(df_all.shape)
print('-' * LINE_WIDTH)
print()

# ------------------------ 4. 过滤无效书籍 ------------------------
now = pd.Timestamp.now()
# 计算书籍从上次更新至今的天数
df_all['days_since_up'] = (now - df_all['up_time']).dt.days

# 无效条件1: 总字数小于200000、更新间隔大于半年、不是出版
cond1 = (df_all['wordcount'] < 200000) & (df_all['days_since_up'] > 180) & (df_all['cate'] != 2)
# 无效条件2: 总字数小于2000、总推荐数为0、不是出版
cond2 = (df_all['wordcount'] < 2000) & (df_all['all_recommend'] == 0) & (df_all['cate'] != 2)

invalid_mask = cond1 | cond2
df_all = df_all[~invalid_mask]
print('清理后书籍数:', len(df_all))
print('移除无效书籍:', invalid_mask.sum())

# 删除辅助列
df_all.drop(columns=['days_since_up'], inplace=True)

# 写入MySQL，表名 'novel_info'
dtype_mapping = {
    'cate': types.SMALLINT,
    'img': types.VARCHAR(255),
    'name': types.VARCHAR(255),
    'author': types.VARCHAR(100),
    'up_time': types.DATETIME,
    'up_chapter': types.VARCHAR(255),
    'up_status': types.SMALLINT,
    'signed': types.SMALLINT,
    'vip': types.SMALLINT,
    'category': types.VARCHAR(100),
    'sub_category': types.VARCHAR(100),
    'wordcount': types.INTEGER,
    'all_recommend': types.INTEGER,
    'week_recommend': types.INTEGER,
    'introduction': types.TEXT,
    'chapters': types.INTEGER,
}
df_all.to_sql('novel_info', con=engine, if_exists='replace', index=False, dtype=dtype_mapping)
print("数据已存入 novel_info 表")

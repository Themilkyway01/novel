import pandas as pd
from sqlalchemy import create_engine

print("\n=== 数据统计验证 ===")
engine = create_engine('mysql+pymysql://root:123456@localhost/novel_data?charset=utf8mb4')
# 读取小说信息
df_behavior = pd.read_sql('SELECT * FROM user_behavior', engine)
print("阅读时长分布:")
print(df_behavior['read_time'].describe())
print("\n每个用户的阅读数量分布:")
user_counts = df_behavior.groupby('user_id').size()
print(user_counts.describe())
print("\n每本书的阅读人数分布:")
item_counts = df_behavior.groupby('novel_id').size()
print(item_counts.describe())

# # 冷启动用户统计
# cold_users = [p['user_id'] for p in user_profiles if p['cold_start']]
# cold_user_records = df_behavior[df_behavior['user_id'].isin(cold_users)]
# print(f"\n冷启动用户数: {len(cold_users)}，平均阅读数: {cold_user_records.groupby('user_id').size().mean():.1f}")
#
# # 各 cate 的用户数分布（检查加权效果）
# cate_user_counts = {0:0, 1:0, 2:0}
# for p in user_profiles:
#     cate_user_counts[p['liked_cate']] += 1
# print(f"\n各 cate 用户数: {cate_user_counts}")
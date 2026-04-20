"""
小说推荐系统 - 主程序入口
功能：数据预处理、模型训练、推荐服务
"""
import pandas as pd
from sqlalchemy import create_engine
from recommender import (
    add_rating_column, filter_sparse_data,
    prepare_surprise_data, train_evaluate_models,
    tune_svd_factors,
    Recommender, UserProfileManager
)
from api import RecommendationAPI, load_recommendation_api


# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'novel_data'
}


def load_data_from_db():
    """从数据库加载数据"""
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    print("加载小说信息...")
    novel_info = pd.read_sql("SELECT * FROM novel_info", engine)
    
    print("加载用户行为...")
    user_behavior = pd.read_sql("SELECT * FROM user_behavior", engine)
    
    engine.dispose()
    return novel_info, user_behavior


def train_model(novel_info: pd.DataFrame, user_behavior: pd.DataFrame):
    """训练推荐模型"""
    import json
    import os
    
    print("\n=== 数据预处理 ===")
    user_behavior, thresholds = add_rating_column(user_behavior)
    filtered, active_users, popular_novels, user_gender_map = filter_sparse_data(user_behavior)
    
    print("\n=== 模型训练 ===")
    data = prepare_surprise_data(filtered)
    
    # SVD隐因子数调优实验
    svd_best_model, best_n_factors, tuning_results = tune_svd_factors(data)
    print(f"\nSVD调优结果：")
    for n_factors, metrics in tuning_results.items():
        print(f"  隐因子数 {n_factors}: RMSE={metrics['rmse']:.4f}, MAE={metrics['mae']:.4f}, Recall={metrics['recall']:.4f}, NDCG={metrics['ndcg']:.4f}")
    print(f"  最优隐因子数: {best_n_factors}, RMSE: {tuning_results[best_n_factors]['rmse']:.4f}, Recall: {tuning_results[best_n_factors]['recall']:.4f}, NDCG: {tuning_results[best_n_factors]['ndcg']:.4f}")

    # 保存调优结果到文件
    tuning_report = {
        'best_n_factors': best_n_factors,
        'best_rmse': tuning_results[best_n_factors]['rmse'],
        'best_mae': tuning_results[best_n_factors]['mae'],
        'best_recall': tuning_results[best_n_factors]['recall'],
        'best_ndcg': tuning_results[best_n_factors]['ndcg'],
        'all_results': {
            str(n_factors): {'rmse': metrics['rmse'], 'mae': metrics['mae'], 'recall': metrics['recall'], 'ndcg': metrics['ndcg']}
            for n_factors, metrics in tuning_results.items()
        }
    }
    with open('svd_tuning_report.json', 'w', encoding='utf-8') as f:
        json.dump(tuning_report, f, indent=2, ensure_ascii=False)
    print("调优报告已保存至 svd_tuning_report.json")
    
    # 使用最优隐因子数训练所有模型并比较（用于评估）
    best_model, results = train_evaluate_models(data, svd_n_factors=best_n_factors)
    
    print("\n=== 模型评估结果 ===")
    for name, metrics in results.items():
        print(f"{name}: RMSE={metrics['rmse']:.4f}, MAE={metrics['mae']:.4f}, Recall={metrics['recall']:.4f}, NDCG={metrics['ndcg']:.4f}")
    print(f"\n最佳模型（比较结果）：{best_model.__class__.__name__}")
    
    # 保存模型（使用最优隐因子数的SVD模型）
    print("\n保存模型...")
    # 使用调优得到的最佳SVD模型
    recommender = Recommender(svd_best_model, novel_info, filtered, user_gender_map)
    recommender.save('svd_model.pkl', 'tfidf.pkl')
    print(f"已保存最优SVD模型（隐因子数={best_n_factors}）至 svd_model.pkl")
    
    return recommender, filtered, user_gender_map


def demo_recommendations(api: RecommendationAPI):
    """演示推荐功能"""
    print("\n=== 推荐演示 ===")
    
    # 热门推荐（未登录）
    print("\n热门推荐（未登录）:")
    hot_recs = api.get_hot_recommendations(n=5)
    for rec in hot_recs:
        print(f"  - {rec['name']} ({rec['category']})")
    
    # 最新更新
    print("\n最新更新:")
    latest = api.get_latest_recommendations(n=5)
    for rec in latest:
        print(f"  - {rec['name']} ({rec['category']})")
    
    # 个性化推荐（登录用户）
    print("\n个性化推荐（用户 1）:")
    personal = api.get_personalized_recommendations(user_id=1, n=5)
    for rec in personal:
        print(f"  - {rec['name']} ({rec['category']}) - 分数：{rec['score']:.2f}")
    
    # 相似小说
    print("\n相似小说推荐（用户 1）:")
    similar = api.get_similar_recommendations(user_id=1, n=5)
    for rec in similar:
        print(f"  - {rec['name']} ({rec['category']})")


def main():
    """主函数"""
    print("=== 小说推荐系统 ===\n")
    
    # 加载数据
    try:
        novel_info, user_behavior = load_data_from_db()
    except Exception as e:
        print(f"数据库连接失败：{e}")
        print("请确保数据库配置正确并运行")
        return
    
    # 训练模型
    recommender, filtered_data, user_gender_map = train_model(novel_info, user_behavior)
    
    # 创建 API
    user_profile_manager = UserProfileManager(novel_info, filtered_data)
    recommender = Recommender.load(
        'svd_model.pkl', 'tfidf.pkl',
        novel_info, filtered_data, user_gender_map,
        user_profile_manager=user_profile_manager
    )
    api = RecommendationAPI(recommender, user_profile_manager)
    
    # 演示推荐
    demo_recommendations(api)
    
    print("\n=== 训练完成 ===")
    print("模型已保存为：svd_model.pkl, tfidf.pkl")
    print("可在 web 后端通过 api.py 调用推荐服务")


if __name__ == '__main__':
    main()

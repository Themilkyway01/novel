"""
小说推荐系统核心模块
包含：数据预处理、模型训练、用户画像、推荐引擎
"""
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import joblib
import random

from surprise import Dataset, Reader, KNNBasic, SVD, accuracy
from surprise.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import jieba

# 中文停用词
STOP_WORDS_CN = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}

def preprocess_chinese_text(text):
    """中文文本预处理：分词、去停用词、过滤短词"""
    if not isinstance(text, str) or not text.strip():
        return ''
    # 分词
    words = jieba.lcut(text)
    # 过滤停用词和长度大于1的词
    words = [w for w in words if w.strip() and w not in STOP_WORDS_CN and len(w) > 1]
    return ' '.join(words)


# ==================== 数据预处理 ====================
def compute_quantile_thresholds(read_time_series: pd.Series) -> List[Tuple[float, int]]:
    """根据阅读时长分布计算分位数阈值"""
    quantiles = read_time_series.quantile([0.2, 0.4, 0.6, 0.8])
    return [
        (quantiles.iloc[0], 1), (quantiles.iloc[1], 2),
        (quantiles.iloc[2], 3), (quantiles.iloc[3], 4),
        (float('inf'), 5)
    ]


def convert_readtime_to_score(read_time: float, thresholds: List[Tuple[float, int]]) -> int:
    """将阅读时长转换为评分"""
    for upper_bound, score in thresholds:
        if read_time < upper_bound:
            return score
    return 5


def add_rating_column(user_behavior: pd.DataFrame) -> Tuple[pd.DataFrame, List[Tuple[float, int]]]:
    """为行为数据添加评分列（基于阅读时长分位数）"""
    user_behavior = user_behavior.copy()
    thresholds = compute_quantile_thresholds(user_behavior['read_time'])
    print('自动计算的分位阈值（min）:\n', thresholds)
    user_behavior['rating'] = user_behavior['read_time'].apply(
        lambda x: convert_readtime_to_score(x, thresholds)
    )
    return user_behavior, thresholds


def filter_sparse_data(user_behavior: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Index, pd.Index, Dict]:
    """过滤冷启动用户和冷门物品，返回过滤后数据和用户性别映射"""
    user_behavior = user_behavior.drop_duplicates(subset=['user_id', 'novel_id'], keep='first')
    
    # 获取用户性别映射
    user_gender_map = user_behavior.groupby('user_id')['user_cate'].agg(
        lambda x: x.mode()[0] if not x.mode().empty else None
    ).to_dict()
    
    user_counts = user_behavior['user_id'].value_counts()
    novel_counts = user_behavior['novel_id'].value_counts()
    
    min_user = max(10, int(user_counts.quantile(0.5)))
    min_novel = max(5, int(novel_counts.quantile(0.5)))
    
    active_users = user_counts[user_counts >= min_user].index
    popular_novels = novel_counts[novel_counts >= min_novel].index
    
    filtered = user_behavior[
        user_behavior['user_id'].isin(active_users) &
        user_behavior['novel_id'].isin(popular_novels)
    ]
    
    print(f'\n过滤后：{len(filtered)}/{len(user_behavior)} 条记录')
    print(f'活跃用户：{len(active_users)}/{len(user_counts)}')
    print(f'热门书籍：{len(popular_novels)}/{len(novel_counts)}')
    
    return filtered, active_users, popular_novels, user_gender_map


# ==================== 评估指标 ====================
def compute_ranking_metrics(predictions, k=10, rating_threshold=4.0, trainset=None, model=None):
    """计算Recall@k和NDCG@k
    Args:
        predictions: list of surprise.Prediction objects
        k: 推荐列表长度
        rating_threshold: 评分阈值，大于等于该值视为正反馈
        trainset: 训练集（Trainset对象），如果提供则使用负样本进行排名评估
        model: 训练好的模型，如果提供则用于预测负样本
    Returns:
        dict with 'recall' and 'ndcg' (averaged over users)
    """
    import numpy as np
    
    # 尝试使用Surprise内置指标（如果可用）
    try:
        from surprise.accuracy import recall_at_k, ndcg_at_k
        recall = recall_at_k(predictions, k=k, threshold=rating_threshold)
        ndcg = ndcg_at_k(predictions, k=k, threshold=rating_threshold)
        return {'recall': recall, 'ndcg': ndcg, 'recall_list': [], 'ndcg_list': []}
    except ImportError:
        # 如果提供了trainset和model，使用负样本排名评估（更准确）
        if trainset is not None and model is not None:
            return compute_ranking_metrics_with_negatives(predictions, k, rating_threshold, trainset, model)
        # 否则回退到改进的自定义实现（仅使用正样本，可能高估）
        from collections import defaultdict
        
        # 按用户分组
        user_predictions = defaultdict(list)
        for pred in predictions:
            uid = pred.uid
            iid = pred.iid
            est = pred.est
            r_ui = pred.r_ui
            user_predictions[uid].append((iid, est, r_ui))
        
        recalls = []
        ndcgs = []
        true_positives_counts = []
        
        for uid, preds in user_predictions.items():
            # 获取真实正样本（评分>=阈值）
            true_positives = [iid for iid, _, r_ui in preds if r_ui >= rating_threshold]
            if not true_positives:
                # 该用户无正样本，跳过
                continue
            
            # 按预测评分排序
            preds.sort(key=lambda x: x[1], reverse=True)
            top_k = preds[:k]
            top_k_items = [iid for iid, _, _ in top_k]
            
            # 计算Recall@k
            hit = len(set(top_k_items) & set(true_positives))
            recall = hit / len(true_positives)
            recalls.append(recall)
            
            # 计算NDCG@k
            # 为每个物品分配相关性分数：1（相关）或0（不相关）
            relevance = [1 if r_ui >= rating_threshold else 0 for _, _, r_ui in preds]
            # 按预测评分排序的相关性列表
            sorted_rel = [relevance[idx] for idx in np.argsort([-est for _, est, _ in preds])]
            dcg = 0.0
            for rank, rel in enumerate(sorted_rel[:k], start=1):
                dcg += rel / np.log2(rank + 1)
            # 理想DCG：按相关性排序
            ideal_rel = sorted(relevance, reverse=True)
            idcg = 0.0
            for rank, rel in enumerate(ideal_rel[:k], start=1):
                idcg += rel / np.log2(rank + 1)
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcgs.append(ndcg)
            true_positives_counts.append(len(true_positives))
        
        avg_recall = np.mean(recalls) if recalls else 0.0
        avg_ndcg = np.mean(ndcgs) if ndcgs else 0.0
        
        # 调试输出：打印统计信息
        if recalls:
            print(f"[DEBUG ranking metrics] 用户数量: {len(recalls)}, 平均真实正样本数: {np.mean(true_positives_counts):.2f}, 平均Recall: {avg_recall:.4f}, 平均NDCG: {avg_ndcg:.4f}")
            print(f"[DEBUG ranking metrics] Recall分布: min={np.min(recalls):.4f}, max={np.max(recalls):.4f}, std={np.std(recalls):.4f}")
            print(f"[DEBUG ranking metrics] 真实正样本数分布: min={np.min(true_positives_counts)}, max={np.max(true_positives_counts)}, avg={np.mean(true_positives_counts):.2f}")
        
        return {'recall': avg_recall, 'ndcg': avg_ndcg, 'recall_list': recalls, 'ndcg_list': ndcgs}


def compute_ranking_metrics_with_negatives(predictions, k, rating_threshold, trainset, model, num_negatives=100):
    """使用负样本计算排名指标（更准确的评估）
    对于每个用户，采样负样本，与正样本混合排序，计算HR@k和NDCG@k
    """
    import numpy as np
    import random
    from collections import defaultdict
    
    # 获取所有物品集合（原始ID）
    all_items_raw = set(trainset.all_items())
    # 将内部ID转换为原始ID
    all_items = set([trainset.to_raw_iid(iid) for iid in all_items_raw])
    
    # 按用户分组正样本（评分>=阈值）
    user_positives = defaultdict(list)
    for pred in predictions:
        if pred.r_ui >= rating_threshold:
            user_positives[pred.uid].append(pred.iid)
    
    hits = []
    ndcgs = []
    
    for uid, pos_items in user_positives.items():
        if not pos_items:
            continue
        
        try:
            user_inner_id = trainset.to_inner_uid(uid)
            # 获取用户已交互的物品（训练集）
            rated_inner = [iid for iid, _ in trainset.ur[user_inner_id]]
            rated = set([trainset.to_raw_iid(iid) for iid in rated_inner])
        except ValueError:
            # 用户不在训练集中（理论上不会发生）
            rated = set()
        # 添加测试集正样本
        rated.update(pos_items)
        
        # 采样负样本
        candidate_negatives = list(all_items - rated)
        if len(candidate_negatives) > num_negatives:
            neg_items = random.sample(candidate_negatives, num_negatives)
        else:
            neg_items = candidate_negatives
        
        # 构建候选物品列表：一个正样本（随机选择一个） + 负样本
        # 注意：这里我们只评估一个正样本，因为每个用户可能有多个正样本，但为简化，随机选一个
        pos_item = random.choice(pos_items)
        candidates = [pos_item] + neg_items
        
        # 预测评分
        candidate_predictions = []
        for iid in candidates:
            pred_obj = model.predict(uid, iid, r_ui=None, clip=False)
            candidate_predictions.append((iid, pred_obj.est))
        
        # 按预测评分排序
        candidate_predictions.sort(key=lambda x: x[1], reverse=True)
        # 获取前k个物品的ID
        top_k_items = [iid for iid, _ in candidate_predictions[:k]]
        
        # 计算Hit Rate@k（是否命中正样本）
        hit = 1 if pos_item in top_k_items else 0
        hits.append(hit)
        
        # 计算NDCG@k（只有一个相关物品）
        # 找到正样本的排名（从1开始）
        rank = next((idx + 1 for idx, (iid, _) in enumerate(candidate_predictions) if iid == pos_item), None)
        if rank is not None:
            dcg = 1 / np.log2(rank + 1)
            idcg = 1 / np.log2(1 + 1)  # 理想排名为1
            ndcg = dcg / idcg
        else:
            ndcg = 0.0
        ndcgs.append(ndcg)
    
    avg_hit = np.mean(hits) if hits else 0.0
    avg_ndcg = np.mean(ndcgs) if ndcgs else 0.0
    
    # 调试输出
    print(f"[DEBUG ranking with negatives] 用户数量: {len(hits)}, HR@{k}: {avg_hit:.4f}, NDCG@{k}: {avg_ndcg:.4f}")
    
    # 注意：为了保持接口一致，返回 recall 字段（实际是 HR）
    return {'recall': avg_hit, 'ndcg': avg_ndcg, 'recall_list': hits, 'ndcg_list': ndcgs}


# ==================== 模型训练 ====================
def prepare_surprise_data(filtered_data: pd.DataFrame):
    """将过滤后的数据转换为 Surprise 数据集"""
    reader = Reader(rating_scale=(1, 5))
    return Dataset.load_from_df(filtered_data[['user_id', 'novel_id', 'rating']], reader)


def train_evaluate_models(data, test_size: float = 0.2, random_seed: int = 42, svd_n_factors: int = 100):
    """训练并评估模型（UserCF、ItemCF、SVD），返回最佳模型"""
    trainset, testset = train_test_split(data, test_size=test_size, random_state=random_seed)
    results = {}
    
    # UserCF
    algo_user = KNNBasic(sim_options={'name': 'cosine', 'user_based': True}, k=40, min_k=5, verbose=False)
    algo_user.fit(trainset)
    pred_user = algo_user.test(testset)
    ranking_user = compute_ranking_metrics(pred_user, k=5, rating_threshold=4.5, trainset=trainset, model=algo_user)
    results['UserCF'] = {'model': algo_user, 'rmse': accuracy.rmse(pred_user, verbose=False), 
                         'mae': accuracy.mae(pred_user, verbose=False),
                         'recall': ranking_user['recall'], 'ndcg': ranking_user['ndcg']}
    
    # ItemCF
    algo_item = KNNBasic(sim_options={'name': 'msd', 'user_based': False, 'min_support': 2}, k=20, min_k=3, verbose=False)
    algo_item.fit(trainset)
    pred_item = algo_item.test(testset)
    ranking_item = compute_ranking_metrics(pred_item, k=5, rating_threshold=4.5, trainset=trainset, model=algo_item)
    results['ItemCF'] = {'model': algo_item, 'rmse': accuracy.rmse(pred_item, verbose=False),
                         'mae': accuracy.mae(pred_item, verbose=False),
                         'recall': ranking_item['recall'], 'ndcg': ranking_item['ndcg']}
    
    # SVD
    algo_svd = SVD(n_factors=svd_n_factors, n_epochs=20, lr_all=0.005, reg_all=0.02, random_state=random_seed)
    algo_svd.fit(trainset)
    pred_svd = algo_svd.test(testset)
    ranking_svd = compute_ranking_metrics(pred_svd, k=5, rating_threshold=4.5, trainset=trainset, model=algo_svd)
    results['SVD'] = {'model': algo_svd, 'rmse': accuracy.rmse(pred_svd, verbose=False),
                      'mae': accuracy.mae(pred_svd, verbose=False),
                      'recall': ranking_svd['recall'], 'ndcg': ranking_svd['ndcg']}
    
    best_name = min(results, key=lambda x: results[x]['rmse'])
    return results[best_name]['model'], results


def tune_svd_factors(data, n_factors_list=[20, 50, 100, 150, 200], test_size: float = 0.2, random_seed: int = 42):
    """
    SVD隐因子数超参数调优实验
    返回最佳模型、最佳参数和所有实验结果
    """
    from surprise import SVD, accuracy
    from surprise.model_selection import train_test_split
    
    trainset, testset = train_test_split(data, test_size=test_size, random_state=random_seed)
    
    results = {}
    best_ndcg = -float('inf')
    best_model = None
    best_n_factors = None
    
    print("\n=== SVD隐因子数调优实验 ===")
    for n_factors in n_factors_list:
        print(f"训练 SVD 模型，隐因子数 = {n_factors}...")
        algo = SVD(n_factors=n_factors, n_epochs=20, lr_all=0.005, reg_all=0.02, random_state=random_seed)
        algo.fit(trainset)
        pred = algo.test(testset)
        rmse = accuracy.rmse(pred, verbose=False)
        mae = accuracy.mae(pred, verbose=False)
        ranking = compute_ranking_metrics(pred, k=5, rating_threshold=4.5, trainset=trainset, model=algo)
        
        results[n_factors] = {'model': algo, 'rmse': rmse, 'mae': mae,
                               'recall': ranking['recall'], 'ndcg': ranking['ndcg']}
        
        print(f"  RMSE = {rmse:.4f}, MAE = {mae:.4f}, Recall = {ranking['recall']:.4f}, NDCG = {ranking['ndcg']:.4f}")
        
        ndcg = ranking['ndcg']
        if ndcg > best_ndcg:
            best_ndcg = ndcg
            best_model = algo
            best_n_factors = n_factors
    
    print(f"\n最佳隐因子数（基于NDCG）: {best_n_factors}, NDCG: {best_ndcg:.4f}")
    
    # 绘制隐因子数与NDCG的关系折线图
    try:
        import matplotlib.pyplot as plt
        import os
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei']

        # 准备数据
        factors = sorted(results.keys())
        ndcgs = [results[f]['ndcg'] for f in factors]
        
        # 创建图形
        plt.figure(figsize=(8, 5))
        plt.plot(factors, ndcgs, marker='o', linestyle='-', linewidth=2, markersize=8)
        plt.xlabel('隐因子数', fontsize=12)
        plt.ylabel('NDCG@5', fontsize=12)
        plt.title('SVD隐因子数 vs NDCG', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        
        # 标记最佳点
        best_idx = factors.index(best_n_factors)
        plt.scatter(best_n_factors, best_ndcg, color='red', s=100, zorder=5, label=f'最佳点 ({best_n_factors}, {best_ndcg:.4f})')
        
        # 添加数据标签
        for i, (factor, ndcg) in enumerate(zip(factors, ndcgs)):
            plt.annotate(f'{ndcg:.4f}', (factor, ndcg), 
                        xytext=(0, 10), textcoords='offset points',
                        ha='center', fontsize=9)
        
        plt.legend()
        plt.tight_layout()
        
        # 保存图形
        plot_path = 'svd_factors_vs_ndcg.png'
        plt.savefig(plot_path, dpi=300)
        plt.close()
        
        print(f"隐因子数-NDCG关系图已保存至: {plot_path}")
        
    except ImportError:
        print("未安装matplotlib，无法生成图形。安装命令: pip install matplotlib")
        # 打印数据点供手动绘图
        print("隐因子数与NDCG数据点:")
        for factor in sorted(results.keys()):
            print(f"  隐因子数 {factor}: NDCG = {results[factor]['ndcg']:.4f}")
    except Exception as e:
        print(f"生成图形时出错: {e}")
    
    return best_model, best_n_factors, results


# ==================== 用户画像 ====================
class UserProfile:
    """用户画像类 - 多维度兴趣建模"""

    def __init__(self, user_id: int, novel_info: pd.DataFrame, user_behavior: pd.DataFrame):
        self.user_id = user_id
        self.novel_info = novel_info.copy()
        
        # 确保 novel_id 列存在
        if 'novel_id' not in self.novel_info.columns:
            if 'index' in self.novel_info.columns:
                self.novel_info.rename(columns={'index': 'novel_id'}, inplace=True)
            elif 'id' in self.novel_info.columns:
                self.novel_info.rename(columns={'id': 'novel_id'}, inplace=True)
            else:
                first_col = self.novel_info.columns[0]
                self.novel_info.rename(columns={first_col: 'novel_id'}, inplace=True)
        
        self.user_behavior = user_behavior[user_behavior['user_id'] == user_id].copy()
        
        self.user_cate = None
        self.channel_weights = {}
        self.category_weights = {}
        self.sub_category_weights = {}
        self.author_weights = {}
        self.tag_weights = {}
        
        self.time_decay_factor = 0.95
        self.diversity_factor = 0.1
        
        if not self.user_behavior.empty:
            self._build_profile()
    
    def _build_profile(self):
        """构建用户画像"""
        user_data = self.user_behavior.merge(self.novel_info, on='novel_id', how='left')
        if user_data.empty:
            return
        
        # 时间衰减权重
        if 'created_at' in user_data.columns:
            timestamps = pd.to_datetime(user_data['created_at'])
            max_time = timestamps.max()
            days_diff = (max_time - timestamps).dt.days
            user_data['time_weight'] = np.power(self.time_decay_factor, days_diff / 7)
        else:
            user_data['time_weight'] = 1.0
        
        user_data['weighted_rating'] = user_data['rating'] * user_data['time_weight']
        
        # 频道偏好
        if 'cate' in user_data.columns:
            channel_scores = user_data.groupby('cate')['weighted_rating'].sum()
            total = channel_scores.sum()
            if total > 0:
                self.channel_weights = (channel_scores / total).to_dict()
                self.user_cate = channel_scores.idxmax()
        
        # 分类偏好
        if 'category' in user_data.columns:
            category_scores = user_data.groupby('category')['weighted_rating'].sum()
            total = category_scores.sum()
            if total > 0:
                self.category_weights = (category_scores / total).to_dict()
        
        # 子分类偏好
        if 'sub_category' in user_data.columns:
            sub_scores = user_data.groupby('sub_category')['weighted_rating'].sum()
            total = sub_scores.sum()
            if total > 0:
                self.sub_category_weights = (sub_scores / total).to_dict()
        
        # 作者偏好
        if 'author' in user_data.columns:
            author_scores = user_data.groupby('author')['weighted_rating'].sum()
            total = author_scores.sum()
            if total > 0:
                self.author_weights = (author_scores / total).to_dict()
        
        # 标签偏好
        if 'tags' in user_data.columns:
            tag_scores = defaultdict(float)
            for _, row in user_data.iterrows():
                tags = str(row.get('tags', '')).split(',') if pd.notna(row.get('tags')) else []
                for tag in tags:
                    if tag.strip():
                        tag_scores[tag.strip()] += row['weighted_rating']
            total = sum(tag_scores.values())
            if total > 0:
                self.tag_weights = {tag: score / total for tag, score in tag_scores.items()}
    
    def get_diversity_exploration_rate(self) -> float:
        """计算多样性探索率（基于兴趣熵）"""
        if self.category_weights:
            weights = list(self.category_weights.values())
            entropy = -sum(w * np.log2(w + 1e-10) for w in weights)
            max_entropy = np.log2(len(weights) + 1e-10)
            if max_entropy > 0:
                concentration = 1 - (entropy / max_entropy)
                return self.diversity_factor + concentration * 0.2
        return self.diversity_factor


class UserProfileManager:
    """用户画像管理器 - 带缓存"""
    
    def __init__(self, novel_info: pd.DataFrame, user_behavior: pd.DataFrame):
        self.novel_info = novel_info
        self.user_behavior = user_behavior
        self.user_profiles = {}
        self._cache_expiration = {}
        self._cache_ttl = 3600
    
    def get_user_profile(self, user_id: int) -> UserProfile:
        """获取用户画像（带缓存）"""
        now = datetime.now().timestamp()
        if user_id in self.user_profiles and now < self._cache_expiration.get(user_id, 0):
            return self.user_profiles[user_id]
        
        profile = UserProfile(user_id, self.novel_info, self.user_behavior)
        self.user_profiles[user_id] = profile
        self._cache_expiration[user_id] = now + self._cache_ttl
        return profile
    
    def update_user_behavior(self, user_id: int, new_behavior: pd.DataFrame):
        """更新用户行为并刷新画像"""
        if user_id in self.user_profiles:
            self.user_profiles[user_id].user_behavior = pd.concat(
                [self.user_profiles[user_id].user_behavior, new_behavior], ignore_index=True
            )
            self.user_profiles[user_id]._build_profile()
            self._cache_expiration[user_id] = datetime.now().timestamp() + self._cache_ttl


# ==================== 推荐引擎 ====================
class Recommender:
    """增强版推荐器 - 支持多种推荐场景"""
    
    def __init__(self, model, novel_info: pd.DataFrame, filtered_data: pd.DataFrame,
                 user_gender_map: Dict, user_profile_manager: Optional[UserProfileManager] = None,
                 skip_preprocessing: bool = False):
        self.model = model
        self.novel_info = novel_info.copy()
        
        # 确保 novel_id 列存在
        if 'novel_id' not in self.novel_info.columns:
            if 'index' in self.novel_info.columns:
                self.novel_info.rename(columns={'index': 'novel_id'}, inplace=True)
            elif 'id' in self.novel_info.columns:
                self.novel_info.rename(columns={'id': 'novel_id'}, inplace=True)
            else:
                # 使用第一列作为 novel_id
                first_col = self.novel_info.columns[0]
                self.novel_info.rename(columns={first_col: 'novel_id'}, inplace=True)

        self.filtered_data = filtered_data
        self.user_gender_map = user_gender_map
        self.user_profile_manager = user_profile_manager
        
        # 构建内容特征
        self.novel_info['content'] = (
            self.novel_info['category'].fillna('') if 'category' in self.novel_info.columns else ''
        ) + ' ' + (
            self.novel_info['sub_category'].fillna('') if 'sub_category' in self.novel_info.columns else ''
        ) + ' ' + (
            self.novel_info['tags'].fillna('') if 'tags' in self.novel_info.columns else ''
        ) + ' ' + (
            self.novel_info['introduction'].fillna('') if 'introduction' in self.novel_info.columns else ''
        )
        
        if not skip_preprocessing:
            # 中文文本预处理：分词、去停用词
            self.novel_info['content'] = self.novel_info['content'].apply(preprocess_chinese_text)
            # TF-IDF（使用默认分词器，因为content已经用空格分开）
            self.tfidf = TfidfVectorizer(stop_words=None, max_features=5000)
            self.tfidf_matrix = self.tfidf.fit_transform(self.novel_info['content'])
        else:
            # 跳过预处理，TF-IDF 将由 load 方法设置
            self.tfidf = None
            self.tfidf_matrix = None
        
        if 'channel' not in self.novel_info.columns:
            self.novel_info['channel'] = self.novel_info.get('cate', 2)
        
        # 配置
        self.diversity_base_rate = 0.1
        self.diversity_max_rate = 0.3
        self.similar_threshold = 0.3
    
    def _filter_by_channel_category(self, df: pd.DataFrame, channel: Optional[int] = None,
                                    category: Optional[str] = None) -> pd.DataFrame:
        """根据频道和分类过滤"""
        result = df.copy()
        if channel is not None:
            result = result[result['cate'] == channel]
        if category is not None:
            result = result[result['category'] == category]
        return result
    
    def _get_user_profile(self, user_id: int) -> UserProfile:
        """获取用户画像"""
        if self.user_profile_manager:
            return self.user_profile_manager.get_user_profile(user_id)
        return UserProfile(user_id, self.novel_info, self.filtered_data)
    
    def _apply_diversity_factor(self, recommendations: pd.DataFrame, user_profile: UserProfile,
                                n: int) -> pd.DataFrame:
        """应用影响因子，添加多样性内容"""
        if recommendations.empty or user_profile is None:
            return recommendations
        
        exploration_rate = user_profile.get_diversity_exploration_rate()
        diversity_count = max(1, int(n * exploration_rate))
        if diversity_count >= n:
            return recommendations
        
        # 获取用户已读分类
        user_read_novels = self.filtered_data[
            self.filtered_data['user_id'] == user_profile.user_id
        ]['novel_id'].tolist()
        
        read_novel_info = self.novel_info[self.novel_info['novel_id'].isin(user_read_novels)]
        read_categories = set(read_novel_info['category'].tolist()) if not read_novel_info.empty else set()
        
        # 从未探索的分类中引入新书
        all_categories = set(self.novel_info['category'].unique())
        unexplored = all_categories - read_categories
        
        if unexplored:
            diversity_books = []
            for cat in list(unexplored)[:diversity_count]:
                cat_books = self.novel_info[self.novel_info['category'] == cat]
                if not cat_books.empty:
                    diversity_books.append(cat_books.sample(n=1, random_state=random.randint(0, 1000000)))
            
            if diversity_books:
                diversity_df = pd.concat(diversity_books, ignore_index=True)
                keep_count = n - diversity_count
                main_recs = recommendations.head(keep_count)
                return pd.concat([main_recs, diversity_df.head(diversity_count)], ignore_index=True)
        
        return recommendations
    
    def random_sample_recommend(self, channel: Optional[int] = None, category: Optional[str] = None,
                                n: int = 12, exclude_novels: Optional[List] = None) -> pd.DataFrame:
        """随机抽样推荐（热门推荐）"""
        candidates = self._filter_by_channel_category(self.novel_info, channel, category)
        if exclude_novels:
            candidates = candidates[~candidates['novel_id'].isin(exclude_novels)]
        
        if candidates.empty:
            candidates = self._filter_by_channel_category(self.novel_info, channel, None)
            if exclude_novels:
                candidates = candidates[~candidates['novel_id'].isin(exclude_novels)]
        
        if candidates.empty:
            return pd.DataFrame()
        
        return candidates.sample(n=min(n, len(candidates)), random_state=random.randint(0, 1000000))
    
    def get_latest_updates(self, channel: Optional[int] = None, category: Optional[str] = None,
                           n: int = 12, days: int = 30, exclude_novels: Optional[List] = None) -> pd.DataFrame:
        """最新更新推荐"""
        if 'up_time' not in self.novel_info.columns:
            return self.random_sample_recommend(channel, category, n, exclude_novels)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        candidates = self.novel_info[self.novel_info['up_time'] >= cutoff_date]
        candidates = self._filter_by_channel_category(candidates, channel, category)
        
        if exclude_novels:
            candidates = candidates[~candidates['novel_id'].isin(exclude_novels)]
        
        if candidates.empty:
            candidates = self._filter_by_channel_category(self.novel_info, channel, category)
            if exclude_novels:
                candidates = candidates[~candidates['novel_id'].isin(exclude_novels)]
        
        if candidates.empty:
            return pd.DataFrame()
        
        return candidates.sort_values('up_time', ascending=False).head(n)
    
    def get_similar_novels(self, novel_id: int, n: int = 5) -> pd.DataFrame:
        """相似小说推荐（基于内容相似度）"""
        target = self.novel_info[self.novel_info['novel_id'] == novel_id]
        if target.empty:
            return pd.DataFrame()
        
        target_idx = target.index[0]
        similarities = cosine_similarity(
            self.tfidf_matrix[target_idx], self.tfidf_matrix
        ).flatten()
        
        novel_indices = np.argsort(similarities)[::-1][1:n+1]
        valid_indices = [i for i in novel_indices if similarities[i] >= self.similar_threshold]
        if not valid_indices:
            valid_indices = novel_indices[:n]
        
        result = self.novel_info.iloc[valid_indices].copy()
        result['similarity_score'] = similarities[valid_indices]
        return result.sort_values('similarity_score', ascending=False)
    
    def get_similar_novels_for_user(self, user_id: int, n: int = 10) -> pd.DataFrame:
        """基于用户历史的相似小说推荐"""
        user_read = self.filtered_data[self.filtered_data['user_id'] == user_id]['novel_id'].tolist()
        if not user_read:
            return self.hybrid_recommend(user_id, n=n)
        
        all_similar = []
        for novel_id in user_read[:5]:
            similar = self.get_similar_novels(novel_id, n=5)
            if not similar.empty:
                all_similar.append(similar)
        
        if not all_similar:
            return self.hybrid_recommend(user_id, n=n)
        
        similar_df = pd.concat(all_similar, ignore_index=True)
        if 'similarity_score' in similar_df.columns:
            similar_df = similar_df.groupby('novel_id').agg({
                'similarity_score': 'mean', 'name': 'first',
                'category': 'first', 'cate': 'first'
            }).reset_index().sort_values('similarity_score', ascending=False)
        
        similar_df = similar_df[~similar_df['novel_id'].isin(user_read)]
        return similar_df.head(n)
    
    def hybrid_recommend(self, user_id: int, channel: Optional[int] = None,
                         category: Optional[str] = None, alpha: float = 0.7,
                         n: int = 10, use_diversity: bool = True) -> pd.DataFrame:
        """混合推荐：CF + 内容 + 影响因子"""
        user_profile = self._get_user_profile(user_id)
        user_read = self.filtered_data[self.filtered_data['user_id'] == user_id]['novel_id'].tolist()
        
        candidates = self._filter_by_channel_category(self.novel_info, channel, category)
        candidates = candidates[~candidates['novel_id'].isin(user_read)]
        if candidates.empty:
            candidates = self.novel_info[~self.novel_info['novel_id'].isin(user_read)]
        if candidates.empty:
            return pd.DataFrame()
        
        # CF 预测
        cf_scores = []
        for _, row in candidates.iterrows():
            try:
                pred = self.model.predict(uid=user_id, iid=row['novel_id']).est
                cf_scores.append(pred)
            except:
                cf_scores.append(3.0)
        
        candidates = candidates.copy()
        candidates['cf_score'] = cf_scores
        
        # 内容相似度
        if user_read:
            read_indices = self.novel_info[self.novel_info['novel_id'].isin(user_read)].index
            if len(read_indices) > 0:
                user_vec = np.asarray(self.tfidf_matrix[read_indices].mean(axis=0)).reshape(1, -1)
                content_sims = cosine_similarity(
                    user_vec, self.tfidf_matrix[candidates.index]
                ).flatten()
                candidates['content_score'] = content_sims
        
        # 混合分数
        if 'content_score' in candidates.columns:
            candidates['hybrid_score'] = alpha * candidates['cf_score'] + (1 - alpha) * candidates['content_score']
        else:
            candidates['hybrid_score'] = candidates['cf_score']
        
        result = candidates.sort_values('hybrid_score', ascending=False).head(n * 2)
        if use_diversity:
            result = self._apply_diversity_factor(result, user_profile, n * 2)
        return result.head(n)
    
    def recommend(self, user_id: Optional[int] = None, channel: Optional[int] = None,
                  category: Optional[str] = None, n: int = 10, use_diversity: bool = True,
                  recommendation_type: str = 'hybrid') -> pd.DataFrame:
        """统一推荐接口"""
        if user_id is None:
            if recommendation_type == 'latest':
                return self.get_latest_updates(channel, category, n)
            return self.random_sample_recommend(channel, category, n)
        
        if recommendation_type == 'similar':
            return self.get_similar_novels_for_user(user_id, n)
        elif recommendation_type == 'latest':
            return self.get_latest_updates(channel, category, n)
        elif recommendation_type == 'hot':
            random_recs = self.random_sample_recommend(channel, category, n // 2)
            hybrid_recs = self.hybrid_recommend(user_id, channel, category, n=n // 2, use_diversity=use_diversity)
            if not random_recs.empty and not hybrid_recs.empty:
                return pd.concat([random_recs, hybrid_recs], ignore_index=True).head(n)
            return random_recs if not random_recs.empty else hybrid_recs
        else:
            return self.hybrid_recommend(user_id, channel, category, n=n, use_diversity=use_diversity)
    
    def save(self, model_path: str, tfidf_path: str):
        """保存模型"""
        joblib.dump(self.model, model_path)
        joblib.dump({'vectorizer': self.tfidf, 'matrix': self.tfidf_matrix}, tfidf_path)
    
    @classmethod
    def load(cls, model_path: str, tfidf_path: str, novel_info: pd.DataFrame,
             filtered_data: pd.DataFrame, user_gender_map: Dict,
             user_profile_manager: Optional[UserProfileManager] = None):
        """加载模型"""
        model = joblib.load(model_path)
        tfidf_data = joblib.load(tfidf_path)
        recommender = cls(model, novel_info, filtered_data, user_gender_map, user_profile_manager,
                          skip_preprocessing=True)
        recommender.tfidf = tfidf_data.get('vectorizer', recommender.tfidf)
        recommender.tfidf_matrix = tfidf_data.get('matrix', recommender.tfidf_matrix)
        return recommender

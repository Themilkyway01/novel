"""
推荐引擎基类
提供单例模式和通用初始化逻辑
"""
import os
import pandas as pd
import joblib
from django.conf import settings
from django.core.cache import cache

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

BASE_DIR = settings.BASE_DIR
MODEL_DIR = os.path.join(BASE_DIR, 'models')


class RecommendationEngine:
    """
    推荐引擎单例类

    职责：
    1. 加载模型和数据
    2. 管理缓存
    3. 提供统一的推荐接口
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 在创建实例后立即初始化
            cls._instance._initialize()
            cls._initialized = True
        return cls._instance

    def __init__(self):
        # 初始化逻辑已在 __new__ 中处理
        pass

    def _initialize(self):
        """加载模型和数据"""
        if getattr(self, '_is_initialized', False):
            return
        print("正在加载推荐模型...")

        model_path = os.path.join(MODEL_DIR, 'svd_model.pkl')
        tfidf_path = os.path.join(MODEL_DIR, 'tfidf.pkl')

        try:
            self.model = joblib.load(model_path)
            tfidf_data = joblib.load(tfidf_path)
            self.tfidf_vectorizer = tfidf_data['vectorizer']
            self.tfidf_matrix = tfidf_data['matrix']

            from api.models import NovelInfo, UserBehavior
            novel_queryset = NovelInfo.objects.all().values()
            self.novel_info = pd.DataFrame(list(novel_queryset))

            behavior_queryset = UserBehavior.objects.all().values(
                'user_id', 'user_cate', 'novel_id', 'read_time'
            )
            self.filtered_data = pd.DataFrame(list(behavior_queryset))

            self.user_gender_map = {}
            user_cate_series = self.filtered_data.groupby('user_id')['user_cate'].first()
            for user_id, user_cate in user_cate_series.items():
                self.user_gender_map[int(user_id)] = int(user_cate)

            self.novel_info['content'] = (
                self.novel_info['category'].fillna('') + ' ' +
                self.novel_info['sub_category'].fillna('') + ' ' +
                (self.novel_info['tags'].fillna('') if 'tags' in self.novel_info.columns else '') + ' ' +
                (self.novel_info['introduction'].fillna('') if 'introduction' in self.novel_info.columns else '')
            )
            # 注意：TF-IDF 矩阵已从文件加载，无需重新预处理文本

            self._build_category_cache()

            print(f"模型加载完成！小说数：{len(self.novel_info)}, 用户行为数：{len(self.filtered_data)}")
            self._is_initialized = True

        except Exception as e:
            print(f"模型加载失败：{e}")
            self.model = None
            self.novel_info = pd.DataFrame()
            self.filtered_data = pd.DataFrame()
            self.user_gender_map = {}
            self.categories_by_channel = {}
            self.sub_categories_by_category = {}

    def _build_category_cache(self):
        """构建分类缓存"""
        if self.novel_info.empty:
            self.categories_by_channel = {}
            self.sub_categories_by_category = {}
            return

        self.categories_by_channel = {}
        for cate in self.novel_info['cate'].unique():
            cats = self.novel_info[self.novel_info['cate'] == cate]['category'].unique().tolist()
            self.categories_by_channel[int(cate)] = cats

        self.sub_categories_by_category = {}
        for cat in self.novel_info['category'].unique():
            sub_cats = self.novel_info[self.novel_info['category'] == cat]['sub_category'].unique().tolist()
            self.sub_categories_by_category[cat] = sub_cats

    def get_user_profile(self, user_id):
        """获取用户画像向量"""
        from api.models import UserBehavior
        try:
            user_behaviors = UserBehavior.objects.filter(user_id=user_id).values_list(
                'novel_id', flat=True
            )
            user_read = list(user_behaviors)

            if not user_read:
                return None

            idx_list = self.novel_info[self.novel_info['index'].isin(user_read)].index
            if len(idx_list) == 0:
                return None

            import numpy as np
            user_profile = self.tfidf_matrix[idx_list].mean(axis=0)
            return np.asarray(user_profile).reshape(1, -1)
        except Exception as e:
            print(f"获取用户画像失败: {e}")
            return None

    def get_user_reading_history(self, user_id):
        """获取用户阅读历史"""
        from api.models import UserBehavior
        try:
            behaviors = UserBehavior.objects.filter(user_id=user_id).values('novel_id', 'read_time')
            return list(behaviors)
        except Exception as e:
            print(f"获取用户阅读历史失败: {e}")
            return []

    def get_user_preferences(self, user_id):
        """获取用户偏好（频道、分类）"""
        from api.models import User
        try:
            user = User.objects.get(id=user_id)
            return {
                'user_cate': user.user_cate,
                'preferred_categories': []
            }
        except User.DoesNotExist:
            return {'user_cate': None, 'preferred_categories': []}

    def _infer_user_categories(self, user_id, limit=3):
        """根据用户阅读历史推断偏好分类"""
        user_behaviors = self.get_user_reading_history(user_id)

        if not user_behaviors:
            return []

        novel_ids = [b['novel_id'] for b in user_behaviors]
        read_novels = self.novel_info[self.novel_info['index'].isin(novel_ids)]
        if read_novels.empty:
            return []

        import numpy as np
        user_behavior_df = pd.DataFrame(user_behaviors)

        if not user_behavior_df.empty and 'read_time' in user_behavior_df.columns:
            read_with_time = read_novels.merge(
                user_behavior_df[['novel_id', 'read_time']],
                left_on='index',
                right_on='novel_id',
                how='left'
            )

            median_read_time = read_with_time['read_time'].median()
            if pd.isna(median_read_time):
                median_read_time = 30
            read_with_time['read_time'] = read_with_time['read_time'].fillna(median_read_time)

            category_stats = read_with_time.groupby('category').agg(
                count=('index', 'count'),
                avg_read_time=('read_time', 'mean')
            ).reset_index()

            max_time = category_stats['avg_read_time'].max()
            if max_time > 0:
                category_stats['normalized_time'] = category_stats['avg_read_time'] / max_time
            else:
                category_stats['normalized_time'] = 1.0

            category_stats['score'] = (
                category_stats['count'] * 0.4 +
                category_stats['normalized_time'] * 0.6
            )

            category_stats = category_stats.sort_values('score', ascending=False)

            result = []
            for _, row in category_stats.head(limit).iterrows():
                category = row['category']
                category_novels = read_with_time[read_with_time['category'] == category]

                sub_category_stats = category_novels.groupby('sub_category').agg(
                    count=('index', 'count'),
                    avg_read_time=('read_time', 'mean')
                ).reset_index()

                if len(sub_category_stats) > 0:
                    sub_max_time = sub_category_stats['avg_read_time'].max()
                    if sub_max_time > 0:
                        sub_category_stats['normalized_time'] = sub_category_stats['avg_read_time'] / sub_max_time
                    else:
                        sub_category_stats['normalized_time'] = 1.0

                    sub_category_stats['score'] = (
                        sub_category_stats['count'] * 0.4 +
                        sub_category_stats['normalized_time'] * 0.6
                    )

                    sub_category_stats = sub_category_stats.sort_values('score', ascending=False)
                    sub_categories = []
                    for _, sub_row in sub_category_stats.iterrows():
                        sub_categories.append({
                            'name': sub_row['sub_category'] if sub_row['sub_category'] else '其他',
                            'count': int(sub_row['count']),
                            'avg_read_time': round(sub_row['avg_read_time'], 1),
                            'score': round(sub_row['score'], 2)
                        })
                else:
                    sub_categories = []

                result.append({
                    'category': category,
                    'count': int(row['count']),
                    'avg_read_time': round(row['avg_read_time'], 1),
                    'score': round(row['score'], 2),
                    'sub_categories': sub_categories
                })

            return result
        else:
            category_counts = read_novels['category'].value_counts().head(limit)
            result = []
            for category, count in category_counts.items():
                result.append({
                    'category': category,
                    'count': int(count),
                    'avg_read_time': 0,
                    'score': float(count),
                    'sub_categories': []
                })
            return result

    def _apply_diversity_factor(self, recommendations, user_id, n, channel=None, category=None):
        """应用影响因子，添加多样性内容"""
        import random

        if len(recommendations) == 0:
            return recommendations

        DIVERSITY_RATIO = 0.2
        diversity_count = max(1, int(n * DIVERSITY_RATIO))
        main_count = n - diversity_count

        if main_count <= 0:
            return recommendations[:n]

        main_recs = recommendations[:main_count]

        user_behaviors = self.get_user_reading_history(user_id)
        user_reads = [b['novel_id'] for b in user_behaviors] if user_behaviors else []
        read_novels = self.novel_info[self.novel_info['index'].isin(user_reads)]
        read_categories = set(read_novels['category'].tolist()) if not read_novels.empty else set()

        all_categories = set(self.novel_info['category'].unique())
        unexplored_categories = all_categories - read_categories

        if unexplored_categories:
            diversity_recs = []
            for cat in list(unexplored_categories)[:diversity_count]:
                cat_novels = self.novel_info[
                    (self.novel_info['category'] == cat) &
                    (~self.novel_info['index'].isin(user_reads))
                ]
                if not cat_novels.empty:
                    cat_novels_sorted = cat_novels.nlargest(
                        min(20, len(cat_novels)),
                        'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                    )
                    sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000000))
                    diversity_recs.append(sampled)

            if diversity_recs:
                diversity_df = pd.concat(diversity_recs, ignore_index=True)
                diversity_df['is_diversity'] = True
                main_recs_df = pd.DataFrame(main_recs) if not isinstance(main_recs, pd.DataFrame) else main_recs
                main_recs_df['is_diversity'] = False

                result = main_recs_df.to_dict('records') if hasattr(main_recs_df, 'to_dict') else main_recs
                diversity_list = diversity_df.to_dict('records')

                result.extend(diversity_list[:diversity_count])
                return result

        if isinstance(main_recs, pd.DataFrame):
            main_recs['is_diversity'] = False
            return main_recs.head(n).to_dict('records')
        return main_recs[:n]

    def _apply_diversity_factor_for_hot_recent(
        self, recommendations, user_id, n, channel, exclude_ids, sort_by_time=False
    ):
        """为热门推荐和最新更新应用影响因子"""
        import random

        if not recommendations or len(recommendations) == 0:
            return recommendations

        diversity_count = max(1, int(n * 0.2))
        main_count = n - diversity_count

        if main_count <= 0:
            return recommendations[:n]

        main_recs = recommendations[:main_count]

        user_reads = self.get_user_reading_history(user_id)
        read_novels = self.novel_info[self.novel_info['index'].isin(user_reads)]
        read_categories = set(read_novels['category'].tolist()) if not read_novels.empty else set()

        diversity_recs = []
        if channel is not None:
            channel_novels = self.novel_info[self.novel_info['cate'] == channel]
            all_categories_in_channel = set(channel_novels['category'].unique())
            unexplored_categories = all_categories_in_channel - read_categories

            if unexplored_categories:
                for cat in list(unexplored_categories):
                    if len(diversity_recs) >= diversity_count:
                        break

                    cat_novels = self.novel_info[
                        (self.novel_info['cate'] == channel) &
                        (self.novel_info['category'] == cat) &
                        (~self.novel_info['index'].isin(exclude_ids))
                    ]
                    if not cat_novels.empty:
                        if sort_by_time:
                            cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                            top_50 = cat_novels_sorted.head(50)
                            if len(top_50) > 0:
                                sampled = top_50.sample(n=1, random_state=random.randint(0, 1000000))
                            else:
                                sampled = cat_novels_sorted.head(1)
                        else:
                            cat_novels_sorted = cat_novels.nlargest(
                                min(20, len(cat_novels)),
                                'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                            )
                            sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000000))
                        diversity_recs.extend(sampled.to_dict('records'))
        else:
            unexplored_categories = set(self.novel_info['category'].unique()) - read_categories
            if unexplored_categories:
                for cat in list(unexplored_categories):
                    if len(diversity_recs) >= diversity_count:
                        break

                    cat_novels = self.novel_info[
                        (self.novel_info['category'] == cat) &
                        (~self.novel_info['index'].isin(exclude_ids))
                    ]
                    if not cat_novels.empty:
                        if sort_by_time:
                            cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                            top_50 = cat_novels_sorted.head(50)
                            if len(top_50) > 0:
                                sampled = top_50.sample(n=1, random_state=random.randint(0, 1000000))
                            else:
                                sampled = cat_novels_sorted.head(1)
                        else:
                            cat_novels_sorted = cat_novels.nlargest(
                                min(20, len(cat_novels)),
                                'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                            )
                            sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000000))
                        diversity_recs.extend(sampled.to_dict('records'))

        if diversity_recs:
            result = main_recs + diversity_recs[:diversity_count]
            return result[:n]

        return main_recs[:n]

    def random_sample_from_categories(self, channel=None, category=None, n=12, exclude_ids=None):
        """从指定频道和分类中随机抽取 n 本书"""
        import random

        if exclude_ids is None:
            exclude_ids = []

        candidates = self.novel_info.copy()

        if channel is not None:
            candidates = candidates[candidates['cate'] == channel]
        if category is not None:
            candidates = candidates[candidates['category'] == category]
        if exclude_ids:
            candidates = candidates[~candidates['index'].isin(exclude_ids)]

        if candidates.empty:
            return []

        if category is not None:
            sampled = candidates.sample(n=min(n, len(candidates)), random_state=random.randint(0, 1000000))
            return sampled.to_dict('records')

        categories = self.categories_by_channel.get(
            channel, []
        ) if channel is not None else list(self.novel_info['category'].unique())

        if not categories:
            return []

        per_category = max(1, n // len(categories))
        remainder = n - per_category * len(categories)

        result = []
        random.shuffle(categories)

        for i, cat in enumerate(categories):
            cat_novels = candidates[candidates['category'] == cat]
            if cat_novels.empty:
                continue

            extra = 1 if i < remainder else 0
            count = per_category + extra

            sampled = cat_novels.sample(
                n=min(count, len(cat_novels)),
                random_state=random.randint(0, 1000000)
            )
            result.extend(sampled.to_dict('records'))

        if len(result) < n:
            remaining = candidates[~candidates['index'].isin([r['index'] for r in result])]
            if not remaining.empty:
                extra_sample = remaining.sample(
                    n=min(n - len(result), len(remaining)),
                    random_state=random.randint(0, 1000000)
                )
                result.extend(extra_sample.to_dict('records'))

        return result[:n]

    def get_hot_recommendations(
        self, user_id=None, channel=None, category=None,
        preferred_categories=None, n=12, skip_cache=False, sort_by_time=False,
        extra_exclude_ids=None
    ):
        """热门推荐"""
        import random

        if preferred_categories and isinstance(preferred_categories, list):
            preferred_categories_sorted = tuple(sorted(preferred_categories))
        else:
            preferred_categories_sorted = None

        if not skip_cache:
            cache_key = f'hot_{user_id}_{channel}_{category}_{preferred_categories_sorted}_{n}_{sort_by_time}'
            cached = cache.get(cache_key)
            if cached:
                print(f'从缓存获取热门推荐: {cache_key}')
                return cached

        exclude_ids = []
        if user_id:
            exclude_ids = self.get_user_reading_history(user_id)
        if extra_exclude_ids:
            exclude_ids = list(set(exclude_ids + extra_exclude_ids))

        if user_id is None or channel is None:
            result = self._sample_by_channel(n, exclude_ids, sort_by_time)
        else:
            if preferred_categories and isinstance(preferred_categories, list) and len(preferred_categories) > 0:
                result = self._sample_from_preferred_categories(
                    preferred_categories, channel, n, exclude_ids, sort_by_time
                )
            elif category is None:
                inferred_categories = self._infer_user_categories(user_id, limit=5)
                if inferred_categories:
                    inferred_category_names = [
                        cat['category'] if isinstance(cat, dict) else cat
                        for cat in inferred_categories
                    ]
                    result = self._sample_from_preferred_categories(
                        inferred_category_names, channel, n, exclude_ids, sort_by_time
                    )
                else:
                    result = self.random_sample_from_categories(channel, None, n, exclude_ids)
            else:
                result = self.random_sample_from_categories(channel, category, n, exclude_ids)

        if user_id and result:
            result = self._apply_diversity_factor_for_hot_recent(
                result, user_id, n, channel, exclude_ids, sort_by_time
            )

        if not skip_cache:
            print(f'缓存热门推荐: {cache_key}, 结果数: {len(result) if result else 0}')
            cache.set(cache_key, result, 300)
        return result

    def _sample_by_channel(self, n=12, exclude_ids=None, sort_by_time=False):
        """按频道等比例分配抽取书籍"""
        import random

        if exclude_ids is None:
            exclude_ids = []

        channel_allocation = {1: 5, 0: 5, 2: 2}
        result = []

        for channel_id, count in channel_allocation.items():
            channel_novels = self.novel_info[
                (self.novel_info['cate'] == channel_id) &
                (~self.novel_info['index'].isin(exclude_ids))
            ]
            if not channel_novels.empty:
                categories = channel_novels['category'].unique().tolist()
                if categories:
                    per_category = max(1, count // len(categories))
                    remainder = count - per_category * len(categories)

                    sampled = []
                    for i, cat in enumerate(categories):
                        cat_novels = channel_novels[channel_novels['category'] == cat]
                        extra = 1 if i < remainder else 0
                        cat_count = per_category + extra

                        if sort_by_time:
                            cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                            top_50 = cat_novels_sorted.head(50)
                            if len(top_50) > 0:
                                cat_sampled = top_50.sample(
                                    n=min(cat_count, len(top_50)),
                                    random_state=random.randint(0, 1000000)
                                )
                            else:
                                cat_sampled = cat_novels_sorted.head(cat_count)
                        else:
                            cat_sampled = cat_novels.sample(
                                n=min(cat_count, len(cat_novels)),
                                random_state=random.randint(0, 1000000)
                            )
                        sampled.extend(cat_sampled.to_dict('records'))
                    result.extend(sampled[:count])
                else:
                    if sort_by_time:
                        sorted_novels = channel_novels.sort_values('up_time', ascending=False)
                        top_50 = sorted_novels.head(50)
                        if len(top_50) > 0:
                            sampled = top_50.sample(
                                n=min(count, len(top_50)),
                                random_state=random.randint(0, 1000000)
                            )
                        else:
                            sampled = sorted_novels.head(count)
                    else:
                        sampled = channel_novels.sample(
                            n=min(count, len(channel_novels)),
                            random_state=random.randint(0, 1000000)
                        )
                    result.extend(sampled.to_dict('records'))

        return result[:n]

    def _sample_from_preferred_categories(
        self, preferred_categories, channel, n, exclude_ids, sort_by_time=False
    ):
        """从用户偏好的分类中抽取书籍"""
        import random

        if not preferred_categories:
            return self.random_sample_from_categories(channel, None, n, exclude_ids)

        result = []
        candidates = self.novel_info[
            (self.novel_info['cate'] == channel) &
            (~self.novel_info['index'].isin(exclude_ids))
        ]

        if candidates.empty:
            return []

        all_channel_categories = set(candidates['category'].unique().tolist())
        valid_preferred = [cat for cat in preferred_categories if cat in all_channel_categories]

        if not valid_preferred:
            return self.random_sample_from_categories(channel, None, n, exclude_ids)

        preferred_count = max(1, int(n * 0.6))
        other_count = n - preferred_count

        per_preferred = max(1, preferred_count // len(valid_preferred))
        remainder = preferred_count - per_preferred * len(valid_preferred)

        for i, cat in enumerate(valid_preferred):
            cat_novels = candidates[candidates['category'] == cat]
            if cat_novels.empty:
                continue

            extra = 1 if i < remainder else 0
            count = per_preferred + extra

            if sort_by_time:
                cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                top_50 = cat_novels_sorted.head(50)
                if len(top_50) > 0:
                    sampled = top_50.sample(
                        n=min(count, len(top_50)),
                        random_state=random.randint(0, 1000000)
                    )
                else:
                    sampled = cat_novels_sorted.head(count)
            else:
                top_novels = cat_novels.nlargest(
                    min(count * 3, len(cat_novels)),
                    'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                )
                sampled = top_novels.sample(
                    n=min(count, len(top_novels)),
                    random_state=random.randint(0, 1000000)
                )
            result.extend(sampled.to_dict('records'))

        other_cats = list(all_channel_categories - set(valid_preferred))
        if other_cats and other_count > 0:
            per_other = max(1, other_count // len(other_cats))
            other_remainder = other_count - per_other * len(other_cats)

            for i, cat in enumerate(other_cats):
                cat_novels = candidates[candidates['category'] == cat]
                if cat_novels.empty:
                    continue

                extra = 1 if i < other_remainder else 0
                count = per_other + extra

                if sort_by_time:
                    cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                    top_50 = cat_novels_sorted.head(50)
                    if len(top_50) > 0:
                        sampled = top_50.sample(
                            n=min(count, len(top_50)),
                            random_state=random.randint(0, 1000000)
                        )
                    else:
                        sampled = cat_novels_sorted.head(count)
                else:
                    top_novels = cat_novels.nlargest(
                        min(count * 2, len(cat_novels)),
                        'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                    )
                    sampled = top_novels.sample(
                        n=min(count, len(top_novels)),
                        random_state=random.randint(0, 1000000)
                    )
                result.extend(sampled.to_dict('records'))

        return result[:n]

    def get_recent_updates(
        self, user_id=None, channel=None, category=None,
        preferred_categories=None, n=12, days=30, skip_cache=False,
        extra_exclude_ids=None
    ):
        """最新更新推荐"""
        if preferred_categories and isinstance(preferred_categories, list):
            preferred_categories_sorted = tuple(sorted(preferred_categories))
        else:
            preferred_categories_sorted = None

        if not skip_cache:
            cache_key = f'recent_{user_id}_{channel}_{category}_{preferred_categories_sorted}_{n}'
            cached = cache.get(cache_key)
            if cached:
                print(f'从缓存获取最新更新: {cache_key}')
                return cached

        result = self.get_hot_recommendations(
            user_id=user_id,
            channel=channel,
            category=category,
            preferred_categories=preferred_categories,
            n=n,
            skip_cache=skip_cache,
            sort_by_time=True,
            extra_exclude_ids=extra_exclude_ids
        )

        if not skip_cache:
            print(f'缓存最新更新: {cache_key}, 结果数: {len(result) if result else 0}')
            cache.set(cache_key, result, 300)
        return result

    def recommend_for_user(self, user_id, n=10, use_hybrid=True, channel=None, category=None):
        """为已登录用户推荐"""
        import numpy as np

        if self.model is None or self.novel_info.empty:
            return []

        cache_key = f'recommend_user_{user_id}_{n}_{channel}_{category}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        read_items = self.get_user_reading_history(user_id)
        all_items = self.novel_info['index'].tolist()
        candidates = [item for item in all_items if item not in read_items]

        if not candidates:
            return []

        candidates_df = self.novel_info[self.novel_info['index'].isin(candidates)]
        if channel is not None:
            candidates_df = candidates_df[candidates_df['cate'] == channel]
        if category is not None:
            candidates_df = candidates_df[candidates_df['category'] == category]

        candidates = candidates_df['index'].tolist()

        if not candidates:
            return []

        predictions = []
        for item_id in candidates[:500]:
            try:
                pred = self.model.predict(uid=user_id, iid=int(item_id)).est
                predictions.append((int(item_id), pred))
            except Exception:
                continue

        if not predictions:
            result = self.get_hot_recommendations(user_id, channel, category, n)
            cache.set(cache_key, result, 60 * 30)
            return result

        predictions.sort(key=lambda x: x[1], reverse=True)
        top_ids = [item[0] for item in predictions[:n * 2]]

        rec_novels = self.novel_info[self.novel_info['index'].isin(top_ids)]

        user_gender = self.user_gender_map.get(user_id)
        if user_gender is not None and user_gender in [0, 1, 2]:
            rec_novels = rec_novels[rec_novels['cate'] == user_gender]

        result = self._apply_diversity_factor(
            rec_novels.to_dict('records'), user_id, n, channel, category
        )

        cache.set(cache_key, result, 60 * 30)
        return result

    def recommend_cold_start(self, user_cate=None, preferred_categories=None, n=10):
        """冷启动推荐（新用户）"""
        if self.novel_info.empty:
            return []

        cache_key = f'cold_start_{user_cate}_{preferred_categories}_{n}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        candidates = self.novel_info.copy()

        if user_cate is not None:
            candidates = candidates[candidates['cate'] == user_cate]

        if preferred_categories:
            candidates = candidates[candidates['category'].isin(preferred_categories)]

        if candidates.empty:
            candidates = self.novel_info.copy()

        if 'all_recommend' in candidates.columns:
            result = candidates.nlargest(n, 'all_recommend').to_dict('records')
        else:
            result = candidates.sample(min(n, len(candidates))).to_dict('records')

        cache.set(cache_key, result, 60 * 60)
        return result

    def similar_novels(self, novel_id, n=10, same_category_priority=True):
        """相似小说推荐"""
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        if self.novel_info.empty:
            return []

        cache_key = f'similar_{novel_id}_{n}_{same_category_priority}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            novel_idx_rows = self.novel_info[self.novel_info['index'] == novel_id]
            if len(novel_idx_rows) == 0:
                return []

            novel_idx = novel_idx_rows.index[0]
            target_novel = novel_idx_rows.iloc[0]
            target_category = target_novel.get('category', '')

            if not hasattr(self, 'tfidf_matrix') or self.tfidf_matrix is None:
                return []

            novel_vector = self.tfidf_matrix[novel_idx]
            all_similarities = cosine_similarity(novel_vector, self.tfidf_matrix).flatten()

            similarities = []
            for i, sim in enumerate(all_similarities):
                if i != novel_idx and sim > 0:
                    similarities.append((i, sim))

            if not similarities:
                return []

            if same_category_priority:
                same_cat_sims = []
                other_cat_sims = []

                for idx, sim in similarities:
                    novel_cat = self.novel_info.iloc[idx].get('category', '')
                    if novel_cat == target_category:
                        same_cat_sims.append((idx, sim, 0))
                    else:
                        other_cat_sims.append((idx, sim, 1))

                same_cat_sims.sort(key=lambda x: x[1], reverse=True)
                other_cat_sims.sort(key=lambda x: x[1], reverse=True)

                same_cat_count = max(1, int(n * 0.8))
                top_indices = [idx for idx, _, _ in same_cat_sims[:same_cat_count]]
                top_indices += [idx for idx, _, _ in other_cat_sims[:n - len(top_indices)]]

                if len(top_indices) < n:
                    remaining = n - len(top_indices)
                    used_indices = set(top_indices)
                    all_sorted = sorted(
                        [(idx, sim) for idx, sim, _ in same_cat_sims + other_cat_sims
                         if idx not in used_indices],
                        key=lambda x: x[1], reverse=True
                    )
                    top_indices += [idx for idx, _ in all_sorted[:remaining]]
            else:
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_indices = [idx for idx, _ in similarities[:n]]

            result = self.novel_info.iloc[top_indices].to_dict('records')
            cache.set(cache_key, result, 60 * 60)
            return result

        except Exception as e:
            print(f"相似小说计算失败：{e}")
            return []

    def similar_novels_for_user(self, user_id, n=10, same_category_priority=True):
        """基于用户阅读历史的相似小说推荐"""
        user_reads = self.get_user_reading_history(user_id)
        if not user_reads:
            return self.get_hot_recommendations(user_id=user_id, n=n)

        recent_reads = user_reads[:5]
        all_similar = []

        for novel_id in recent_reads:
            similar = self.similar_novels(novel_id, n=5, same_category_priority=same_category_priority)
            all_similar.extend(similar)

        if not all_similar:
            return self.get_hot_recommendations(user_id=user_id, n=n)

        novel_counts = {}
        for novel in all_similar:
            idx = novel['index']
            if idx not in user_reads:
                if idx not in novel_counts:
                    novel_counts[idx] = {'novel': novel, 'count': 0}
                novel_counts[idx]['count'] += 1

        sorted_novels = sorted(novel_counts.values(), key=lambda x: x['count'], reverse=True)
        return [item['novel'] for item in sorted_novels[:n]]

    def recommend_new_books(self, user_id=None, n=10, days=30):
        """新书推荐"""
        from datetime import datetime, timedelta

        if self.novel_info.empty:
            return []

        recent_date = datetime.now() - timedelta(days=days)
        new_books = self.novel_info[self.novel_info['up_time'] >= recent_date].copy()

        if 'chapters' in new_books.columns:
            new_books = new_books[new_books['chapters'] < 100]

        if new_books.empty:
            return []

        if user_id:
            user_profile = self.get_user_profile(user_id)
            if user_profile is not None:
                from sklearn.metrics.pairwise import cosine_similarity
                new_books_idx = new_books.index
                similarities = cosine_similarity(
                    user_profile,
                    self.tfidf_matrix[new_books_idx]
                ).flatten()
                new_books['similarity'] = similarities
                new_books = new_books.sort_values('similarity', ascending=False)
        else:
            if 'all_recommend' in new_books.columns:
                new_books = new_books.nlargest(n, 'all_recommend')

        return new_books.head(n).to_dict('records')

    def get_categories_by_channel(self, channel=None):
        """获取指定频道的分类列表"""
        if channel is None:
            return list(self.novel_info['category'].unique())
        return self.categories_by_channel.get(int(channel), [])

    def get_sub_categories_by_category(self, category):
        """获取指定分类的子分类列表"""
        return self.sub_categories_by_category.get(category, [])


# 全局推荐引擎实例
recommendation_engine = RecommendationEngine()

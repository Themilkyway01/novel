"""
采样策略模块
处理热门推荐、最新更新等采样逻辑
"""
import random
import pandas as pd
from django.core.cache import cache

from .base import recommendation_engine


class SamplingStrategy:
    """采样策略类"""

    def __init__(self, engine):
        self.engine = engine

    def random_sample_from_categories(
        self, channel=None, category=None, n=12, exclude_ids=None
    ):
        """从指定频道和分类中随机抽取 n 本书"""
        if exclude_ids is None:
            exclude_ids = []

        candidates = self.engine.novel_info.copy()

        if channel is not None:
            candidates = candidates[candidates['cate'] == channel]
        if category is not None:
            candidates = candidates[candidates['category'] == category]
        if exclude_ids:
            candidates = candidates[~candidates['index'].isin(exclude_ids)]

        if candidates.empty:
            return []

        if category is not None:
            sampled = candidates.sample(
                n=min(n, len(candidates)),
                random_state=random.randint(0, 1000000)
            )
            return sampled.to_dict('records')

        categories = self.engine.categories_by_channel.get(
            channel, []
        ) if channel is not None else list(self.engine.novel_info['category'].unique())

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
        if preferred_categories and isinstance(preferred_categories, list):
            preferred_categories_sorted = tuple(sorted(preferred_categories))
        else:
            preferred_categories_sorted = None

        if not skip_cache:
            cache_key = f'hot_{user_id}_{channel}_{category}_{preferred_categories_sorted}_{n}_{sort_by_time}'
            cached = cache.get(cache_key)
            if cached:
                return cached

        

        if user_id is None or channel is None:
            result = self._sample_by_channel(n, exclude_ids, sort_by_time)
        else:
            if preferred_categories and isinstance(preferred_categories, list) and len(preferred_categories) > 0:
                result = self._sample_from_preferred_categories(
                    preferred_categories, channel, n, exclude_ids, sort_by_time
                )
            elif category is None:
                inferred_categories = self.engine._infer_user_categories(user_id, limit=5)
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
            result = self.engine._apply_diversity_factor_for_hot_recent(
                result, user_id, n, channel, exclude_ids, sort_by_time
            )

        if not skip_cache:
            cache.set(cache_key, result, 300)
        return result

    def _sample_by_channel(self, n=12, exclude_ids=None, sort_by_time=False):
        """按频道等比例分配抽取书籍"""
        if exclude_ids is None:
            exclude_ids = []

        channel_allocation = {1: 5, 0: 5, 2: 2}
        result = []

        for channel_id, count in channel_allocation.items():
            channel_novels = self.engine.novel_info[
                (self.engine.novel_info['cate'] == channel_id) &
                (~self.engine.novel_info['index'].isin(exclude_ids))
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
        if not preferred_categories:
            return self.random_sample_from_categories(channel, None, n, exclude_ids)

        result = []
        candidates = self.engine.novel_info[
            (self.engine.novel_info['cate'] == channel) &
            (~self.engine.novel_info['index'].isin(exclude_ids))
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
            cache.set(cache_key, result, 300)
        return result


# 全局采样策略实例
sampling_strategy = SamplingStrategy(recommendation_engine)

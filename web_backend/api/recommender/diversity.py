"""
多样性因子模块
处理推荐结果的多样性，确保避免信息茧房
"""
import random

from .base import recommendation_engine


# 影响因子配置
DIVERSITY_RATIO = 0.2


class DiversityHandler:
    """多样性处理类"""

    def __init__(self, engine):
        self.engine = engine

    def _apply_diversity_factor(
        self, recommendations, user_id, n, channel=None, category=None
    ):
        """
        应用影响因子，添加多样性内容避免信息茧房
        策略：80% 主推荐 + 20% 探索性推荐
        """
        if len(recommendations) == 0:
            return recommendations

        diversity_count = max(1, int(n * DIVERSITY_RATIO))
        main_count = n - diversity_count

        if main_count <= 0:
            return recommendations[:n]

        main_recs = recommendations[:main_count]

        user_behaviors = self.engine.get_user_reading_history(user_id)
        user_reads = [b['novel_id'] for b in user_behaviors] if user_behaviors else []
        read_novels = self.engine.novel_info[
            self.engine.novel_info['index'].isin(user_reads)
        ]
        read_categories = set(read_novels['category'].tolist()) if not read_novels.empty else set()

        all_categories = set(self.engine.novel_info['category'].unique())
        unexplored_categories = all_categories - read_categories

        if unexplored_categories:
            diversity_recs = []
            for cat in list(unexplored_categories)[:diversity_count]:
                cat_novels = self.engine.novel_info[
                    (self.engine.novel_info['category'] == cat) &
                    (~self.engine.novel_info['index'].isin(user_reads))
                ]
                if not cat_novels.empty:
                    cat_novels_sorted = cat_novels.nlargest(
                        min(20, len(cat_novels)),
                        'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                    )
                    sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000))
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
        if not recommendations or len(recommendations) == 0:
            return recommendations

        diversity_count = max(1, int(n * 0.2))
        main_count = n - diversity_count

        if main_count <= 0:
            return recommendations[:n]

        main_recs = recommendations[:main_count]

        user_reads = self.engine.get_user_reading_history(user_id)
        read_novels = self.engine.novel_info[
            self.engine.novel_info['index'].isin(user_reads)
        ]
        read_categories = set(read_novels['category'].tolist()) if not read_novels.empty else set()

        diversity_recs = []
        if channel is not None:
            channel_novels = self.engine.novel_info[
                self.engine.novel_info['cate'] == channel
            ]
            all_categories_in_channel = set(channel_novels['category'].unique())
            unexplored_categories = all_categories_in_channel - read_categories

            if unexplored_categories:
                for cat in list(unexplored_categories):
                    if len(diversity_recs) >= diversity_count:
                        break

                    cat_novels = self.engine.novel_info[
                        (self.engine.novel_info['cate'] == channel) &
                        (self.engine.novel_info['category'] == cat) &
                        (~self.engine.novel_info['index'].isin(exclude_ids))
                    ]
                    if not cat_novels.empty:
                        if sort_by_time:
                            cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                            top_50 = cat_novels_sorted.head(50)
                            if len(top_50) > 0:
                                sampled = top_50.sample(n=1, random_state=random.randint(0, 1000))
                            else:
                                sampled = cat_novels_sorted.head(1)
                        else:
                            cat_novels_sorted = cat_novels.nlargest(
                                min(20, len(cat_novels)),
                                'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                            )
                            sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000))
                        diversity_recs.extend(sampled.to_dict('records'))
        else:
            unexplored_categories = set(self.engine.novel_info['category'].unique()) - read_categories
            if unexplored_categories:
                for cat in list(unexplored_categories):
                    if len(diversity_recs) >= diversity_count:
                        break

                    cat_novels = self.engine.novel_info[
                        (self.engine.novel_info['category'] == cat) &
                        (~self.engine.novel_info['index'].isin(exclude_ids))
                    ]
                    if not cat_novels.empty:
                        if sort_by_time:
                            cat_novels_sorted = cat_novels.sort_values('up_time', ascending=False)
                            top_50 = cat_novels_sorted.head(50)
                            if len(top_50) > 0:
                                sampled = top_50.sample(n=1, random_state=random.randint(0, 1000))
                            else:
                                sampled = cat_novels_sorted.head(1)
                        else:
                            cat_novels_sorted = cat_novels.nlargest(
                                min(20, len(cat_novels)),
                                'all_recommend' if 'all_recommend' in cat_novels.columns else 'week_recommend'
                            )
                            sampled = cat_novels_sorted.sample(n=1, random_state=random.randint(0, 1000))
                        diversity_recs.extend(sampled.to_dict('records'))

        if diversity_recs:
            result = main_recs + diversity_recs[:diversity_count]
            return result[:n]

        return main_recs[:n]


# 导入需要的pandas
import pandas as pd

# 全局多样性处理器实例
diversity_handler = DiversityHandler(recommendation_engine)

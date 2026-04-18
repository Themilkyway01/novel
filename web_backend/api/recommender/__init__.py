"""
推荐引擎模块

模块说明：
- base.py      : 推荐引擎基类和完整实现
- collaborative.py : 协同过滤推荐逻辑（备用）
- content.py   : 内容相似度推荐（备用）
- sampling.py  : 采样策略（备用）
- diversity.py : 多样性因子处理（备用）
"""
from .base import RecommendationEngine, recommendation_engine

__all__ = ['RecommendationEngine', 'recommendation_engine']

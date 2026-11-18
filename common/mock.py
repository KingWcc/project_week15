"""Deterministic offline mode for demos and tests.

This is intentionally rule-based and is *not* a replacement for the LLM.  It
exists so that the graph wiring, API, frontend and Docker health checks can be
exercised without credentials or network access.
"""

from __future__ import annotations

import re

from .schemas import SentimentResult

_POSITIVE_TERMS = (
    "开心",
    "高兴",
    "快乐",
    "幸福",
    "兴奋",
    "期待",
    "喜欢",
    "热爱",
    "满意",
    "顺利",
    "成功",
    "通过",
    "录取",
    "升职",
    "加薪",
    "获奖",
    "赢了",
    "太棒",
    "真好",
    "幸运",
    "感激",
    "感谢",
    "自豪",
    "轻松",
    "惊喜",
    "赞",
)

_NEGATIVE_TERMS = (
    "难过",
    "伤心",
    "痛苦",
    "焦虑",
    "压力",
    "好累",
    "疲惫",
    "崩溃",
    "失望",
    "失败",
    "孤独",
    "害怕",
    "担心",
    "烦",
    "生气",
    "愤怒",
    "委屈",
    "抑郁",
    "分手",
    "失业",
    "挂科",
    "糟糕",
    "难受",
    "被骂",
    "无助",
    "想哭",
    "不开心",
    "不高兴",
    "不顺利",
    "不如意",
)

_NEGATIONS = "不没未别莫"


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    total = 0
    for term in terms:
        for match in re.finditer(re.escape(term), text):
            prefix = text[max(0, match.start() - 1) : match.start()]
            if prefix and prefix[-1] in _NEGATIONS:
                continue
            total += 1
    return total


def analyze_mock(message: str) -> SentimentResult:
    positive_hits = _count_terms(message, _POSITIVE_TERMS)
    negative_hits = _count_terms(message, _NEGATIVE_TERMS)

    if positive_hits > negative_hits:
        label = "positive"
        reason = f"离线演示规则检测到 {positive_hits} 处正向情绪线索。"
    elif negative_hits > positive_hits:
        label = "negative"
        reason = f"离线演示规则检测到 {negative_hits} 处负向情绪线索。"
    else:
        label = "neutral"
        reason = "离线演示规则未发现明显占优的正向或负向线索。"

    difference = abs(positive_hits - negative_hits)
    if label == "neutral":
        confidence = 0.60
    else:
        confidence = round(min(0.98, 0.70 + 0.08 * difference), 2)

    return SentimentResult(label=label, confidence=confidence, reason=reason)


_POSITIVE_REPLIES = (
    "这份开心很有分量，值得被好好看见。把今天让你高兴的细节记下来吧，过些日子回看，它还会继续给你力量。",
    "真替你高兴。你的投入和坚持在这一刻有了回声，允许自己完整地享受这份喜悦，也别忘了对自己说一声“我做得不错”。",
    "听到这样的好消息，我也跟着轻松起来。愿你把这份好心情留久一点，带着它去做一件一直想做的事。",
)

_NEGATIVE_REPLIES = (
    "听起来这件事真的消耗了你很多，难受并不是你不够坚强。先不用急着振作，给自己几分钟慢慢呼吸；等稍微缓过来，再去喝口水或走一走，照顾好当下的自己。",
    "你的委屈和疲惫是真实的，不需要马上被解决，也不该被轻轻带过。如果愿意，可以先把最压在心口的那句话写下来；今天先完成一件最小的事，就已经很好。",
    "此刻的你像是在独自扛着一些重量，能说出来已经很不容易。先找一个可信任的人说一说，或者让自己离开压力源一会儿；你不必一个人把所有事都处理完。",
)

_NEUTRAL_REPLIES = (
    "我听到了。你像是在梳理一件还没有完全落定的事，不用急着给自己一个结论。你此刻最想弄清楚的，是哪一部分呢？",
    "谢谢你愿意说这些。它可能还没有明显的喜怒倾向，但你的感受依然值得被认真对待。可以先从最具体的那一点说起。",
    "我在听。暂时没有鲜明的情绪也没关系，很多感受本来就需要时间浮现。给自己一点空间，想到什么再继续说。",
)


def build_mock_reply(message: str, label: str) -> str:
    replies = {
        "positive": _POSITIVE_REPLIES,
        "negative": _NEGATIVE_REPLIES,
        "neutral": _NEUTRAL_REPLIES,
    }[label]
    index = sum(ord(char) for char in message) % len(replies)
    return replies[index]

import re


def normalize_label(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()


def normalize_text(value: str) -> str:
    return normalize_label(value)


def levenshtein_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def levenshtein_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return round(1 - levenshtein_distance(left, right) / max(len(left), len(right)), 4)

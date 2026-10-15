import re
def tokenize(text: str) -> list[str]:
    # Keeps admission codes and numbers intact; underthesea is intentionally optional.
    return re.findall(r'[\wÀ-ỹ]+(?:[./-][\wÀ-ỹ]+)*', text.lower(), flags=re.UNICODE)

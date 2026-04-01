SUBTITLE_STYLES = {}


def register_style(cls):
    SUBTITLE_STYLES[cls.name] = cls
    return cls


def get_style(name):
    if name not in SUBTITLE_STYLES:
        raise ValueError(f"Unknown subtitle style '{name}'. Available: {list(SUBTITLE_STYLES.keys())}")
    return SUBTITLE_STYLES[name]


def list_styles():
    return list(SUBTITLE_STYLES.values())

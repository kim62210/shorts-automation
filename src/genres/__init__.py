GENRES = {}


def register_genre(cls):
    GENRES[cls.name] = cls
    return cls


def get_genre(name):
    if name not in GENRES:
        raise ValueError(f"Unknown genre '{name}'. Available: {list(GENRES.keys())}")
    return GENRES[name]


def list_genres():
    return list(GENRES.values())

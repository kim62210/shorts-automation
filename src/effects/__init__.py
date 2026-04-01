EFFECTS = {}


def register_effect(cls):
    EFFECTS[cls.name] = cls
    return cls


def get_effect(name):
    if name not in EFFECTS:
        raise ValueError(f"Unknown effect '{name}'. Available: {list(EFFECTS.keys())}")
    return EFFECTS[name]


def list_effects():
    return list(EFFECTS.values())

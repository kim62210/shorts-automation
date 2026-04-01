from termcolor import colored


def error(message: str, show_emoji: bool = True) -> None:
    emoji = "❌" if show_emoji else ""
    print(colored(f"{emoji} {message}", "red"))


def success(message: str, show_emoji: bool = True) -> None:
    emoji = "✅" if show_emoji else ""
    print(colored(f"{emoji} {message}", "green"))


def info(message: str, show_emoji: bool = True) -> None:
    emoji = "ℹ️" if show_emoji else ""
    print(colored(f"{emoji} {message}", "magenta"))


def warning(message: str, show_emoji: bool = True) -> None:
    emoji = "⚠️" if show_emoji else ""
    print(colored(f"{emoji} {message}", "yellow"))


def question(message: str, show_emoji: bool = True) -> str:
    emoji = "❓" if show_emoji else ""
    return input(colored(f"{emoji} {message}", "magenta"))

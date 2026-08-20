from enum import Enum


class FormState(str, Enum):
    IDLE = "idle"
    STEP1 = "step1"
    STEP2 = "step2"
    EXPERIENCE = "experience"
    MANUAL_CONFIRM = "manual_confirm"
    NO_EXP_INTRO = "no_exp_intro"
    TIME_DEDICATION = "time_dedication"
    CS2_PRIME = "cs2_prime"


class UserSession:
    def __init__(self) -> None:
        self.state: FormState = FormState.IDLE
        self.geo: str | None = None
        self.has_experience: bool = True
        self.experience_text: str | None = None
        self.time_dedication: str | None = None
        self.cs2_prime: str | None = None
        self.form_message_id: int | None = None
        self.manual_path: str | None = None


_sessions: dict[int, UserSession] = {}


def get_session(user_id: int) -> UserSession:
    if user_id not in _sessions:
        _sessions[user_id] = UserSession()
    return _sessions[user_id]


def reset_session(user_id: int) -> None:
    _sessions.pop(user_id, None)

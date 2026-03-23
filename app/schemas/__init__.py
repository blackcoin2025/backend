# =========================
# AUTH
# =========================
from .auth_schemat import (
    RegisterRequest,
    GenerateCodeRequest,
    LoginRequest,
    EmailRequestSchema,
    VerifyEmailRequest,
    EmailOnlySchema,
    VerificationSchema,
)

# =========================
# TASKS
# =========================
from .task_schemat import (
    CompleteTasksRequest,
    ReferralFriend,
    PromoCodeResponse,
    AddMiningPayload,
    MiningStatusResponse,
    AddMiningResponse,
    TaskBase,
    TaskSchema,
    UserTaskBase,
    UserTaskSchema,
    UserDailyTaskSchema,
)

# =========================
# USER
# =========================
from .user_schemat import (
    UserOut,
)

# =========================
# ACTIONS
# =========================
from .action_schemat import (
    ActionCategoryEnum,
    ActionTypeEnum,
    ActionStatusEnum,
    ActionBase,
    ActionSchema,
    UserActionBase,
    UserActionSchema,
    UserActionsList,
)

# =========================
# BONUS
# =========================
from .bonus_schemat import (
    BonusStatus,
    BonusBase,
    BonusCreate,
    BonusOut,
)

# =========================
# PACK
# =========================
from .pack_schemat import (
    UserPackSchema,
    PackBase,
    PackSchema,
)
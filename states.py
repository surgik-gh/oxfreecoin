from aiogram.fsm.state import State, StatesGroup

# ===== КАПЧА И РЕГИСТРАЦИЯ =====
class Registration(StatesGroup):
    captcha = State()
    server = State()
    nickname = State()
    avatar = State()
    description = State()

# ===== ЗАДАНИЯ =====
class CreateGameTask(StatesGroup):
    category = State()
    resource = State()
    amount = State()
    server = State()
    description = State()
    reward = State()

class CreateCardTask(StatesGroup):
    name = State()
    link = State()
    description = State()
    reward = State()

class SubmitTask(StatesGroup):
    proof = State()

class BuyTask(StatesGroup):
    select_type = State()
    select_item = State()
    select_amount = State()

# ===== ВЫВОД =====
class WithdrawMoney(StatesGroup):
    game_id = State()

class RejectWithdraw(StatesGroup):
    reason = State()

# ===== ИГРЫ =====
class PlayGame(StatesGroup):
    bet = State()
    bet_type = State()  # real / demo
    cube_guess = State()
    minesweeper = State()
    roulette = State()

# ===== ПРОМОКОДЫ =====
class CreatePromo(StatesGroup):
    code = State()
    coins = State()
    uses = State()

class EnterPromo(StatesGroup):
    code = State()

class YouTuberPromo(StatesGroup):
    coins_per_use = State()
    max_uses = State()

# ===== АДМИНКА =====
class AddAdmin(StatesGroup):
    user_id = State()
    clan = State()
    nick = State()
    server = State()

class UpdateAdminProfile(StatesGroup):
    server = State()
    clan = State()
    nick = State()

class RejectSubmission(StatesGroup):
    comment = State()

class ManageUser(StatesGroup):
    search = State()
    balance_change = State()
    privilege_select = State()

# ===== РЫНОК =====
class CreateMarketItem(StatesGroup):
    name = State()
    price = State()
    description = State()
    reward_type = State()  # coins, privilege, promo_ability
    reward_value = State()

# ===== АНКЕТЫ =====
class PlayerProfile(StatesGroup):
    age = State()
    hours = State()
    name = State()
    nickname = State()
    server = State()
    prev_clans = State()

class ClanProfile(StatesGroup):
    name = State()
    tag = State()
    avatar = State()
    founded = State()
    server = State()
    hours_required = State()

# ====New====
class Broadcast(StatesGroup):
    message = State()
    confirm = State()

class CreateUserOrder(StatesGroup):
    category = State()
    resource = State()
    amount = State()
    description = State()

class AddSubscriptionChannel(StatesGroup):
    channel_id = State()
    channel_name = State()
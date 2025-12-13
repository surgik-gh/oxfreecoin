from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict
import math

from config import (
    RESOURCES_CATEGORIES, WITHDRAW_PACKS, TELEGRAM_CHANNEL,
    WEAPON_PRICES, PRIVILEGES, TASKS_PER_PAGE, CAPTCHA_EMOJIS,
    ROULETTE_MULTIPLIERS, TASK_COMMISSION
)

# ===== ГЛАВНОЕ МЕНЮ =====
def get_main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks_menu")],
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="my_balance"),
            InlineKeyboardButton(text="🎮 Игры", callback_data="games_menu")
        ],
        [InlineKeyboardButton(text="🏆 Лидерборд", callback_data="top_players")],
        [
            InlineKeyboardButton(text="🛒 Рынок", callback_data="market_menu"),
            InlineKeyboardButton(text="👥 Тиммейты", callback_data="teams_menu")
        ],
        [InlineKeyboardButton(text="📢 Подписки", callback_data="subscriptions_menu")],
        [InlineKeyboardButton(text="🎁 Промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="📺 Наш канал", url=TELEGRAM_CHANNEL)],
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

# ===== КАПЧА =====
def get_captcha_keyboard(correct_emoji: str, all_emojis: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emoji in all_emojis:
        builder.add(InlineKeyboardButton(text=emoji, callback_data=f"captcha_{emoji}"))
    builder.adjust(5)
    return builder.as_markup()

# ===== РЕГИСТРАЦИЯ =====
def get_skip_button(next_step: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_{next_step}")]
    ])

# ===== БАЛАНС =====
def get_balance_menu(is_youtuber: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💸 Вывести монеты", callback_data="withdraw_menu")],
        [InlineKeyboardButton(text="⭐ Купить монеты", callback_data="buy_coins")],
        [InlineKeyboardButton(text="🎮 Мини-игры", callback_data="games_menu")],
        [InlineKeyboardButton(text="📜 История", callback_data="balance_history")],
    ]
    
    if is_youtuber:
        buttons.insert(-1, [InlineKeyboardButton(text="🎬 Создать промокод", callback_data="youtuber_promo")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_withdraw_packs(user_balance: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for pack_id, pack in WITHDRAW_PACKS.items():
        if user_balance >= pack['coins']:
            text = f"✅ {pack['emoji']} {pack['coins']} монет"
            callback = f"withdraw_{pack_id}"
        else:
            text = f"❌ {pack['emoji']} {pack['coins']} монет"
            callback = "not_enough"
        builder.row(InlineKeyboardButton(text=text, callback_data=callback))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="my_balance"))
    return builder.as_markup()

def get_buy_coins_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 50 звёзд = 10 монет", callback_data="buy_stars_10")],
        [InlineKeyboardButton(text="⭐ 250 звёзд = 50 монет", callback_data="buy_stars_50")],
        [InlineKeyboardButton(text="⭐ 500 звёзд = 100 монет", callback_data="buy_stars_100")],
        [InlineKeyboardButton(text="⭐ 2500 звёзд = 500 монет", callback_data="buy_stars_500")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_balance")]
    ])
# ===== ЗАДАНИЯ =====
def get_tasks_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Открытые заказы", callback_data="open_orders_0")],
        [InlineKeyboardButton(text="➕ Создать заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="💳 Задания с картами", callback_data="card_tasks_0")],
        [InlineKeyboardButton(text="📢 Задания с подписками", callback_data="subscriptions_menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_game_tasks_list(tasks: List[Dict], page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        category = RESOURCES_CATEGORIES.get(task['resource_category'], {})
        emoji = category.get('emoji', '📦')
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {task['resource_amount']}x | 💰{task['reward']}",
            callback_data=f"view_game_task_{task['id']}"
        ))
    
    # Пагинация
    total_pages = math.ceil(total / TASKS_PER_PAGE)
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"game_tasks_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="none"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"game_tasks_{page+1}"))
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu"))
    return builder.as_markup()

def get_card_tasks_list(tasks: List[Dict], page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        builder.row(InlineKeyboardButton(
            text=f"💳 {task['card_name'][:20]} | 💰{task['reward']}",
            callback_data=f"view_card_task_{task['id']}"
        ))
    
    total_pages = math.ceil(total / TASKS_PER_PAGE)
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"card_tasks_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="none"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"card_tasks_{page+1}"))
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu"))
    return builder.as_markup()

def get_task_action_buttons(task_id: int, task_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнить", callback_data=f"submit_{task_type}_{task_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"{task_type}_tasks_0")]
    ])

# ===== ПОКУПКА ЗАДАНИЙ =====
def get_buy_task_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Компоненты", callback_data="buy_task_components")],
        [InlineKeyboardButton(text="🔫 Оружие", callback_data="buy_task_weapons")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu")]
    ])

def get_weapons_list() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for weapon_id, price in WEAPON_PRICES.items():
        name = RESOURCES_CATEGORIES['weapons']['items'].get(weapon_id, weapon_id)
        builder.row(InlineKeyboardButton(
            text=f"🔫 {name} — {price} монет",
            callback_data=f"buy_weapon_{weapon_id}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="buy_task"))
    return builder.as_markup()

def get_component_amount() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amount in [1, 5, 10, 15, 20]:
        builder.add(InlineKeyboardButton(
            text=f"{amount} шт",
            callback_data=f"buy_comp_{amount}"
        ))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="buy_task"))
    return builder.as_markup()

# ===== ИГРЫ =====
def get_games_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Кубик (x2)", callback_data="game_cube")],
        [InlineKeyboardButton(text="🏀 Баскетбол (x2)", callback_data="game_basketball")],
        [InlineKeyboardButton(text="🎯 Дартс (x2)", callback_data="game_darts")],
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton(text="💣 Сапёр (до x5)", callback_data="game_minesweeper")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_balance")]
    ])

def get_bet_type_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Реальные монеты", callback_data="bet_real")],
        [InlineKeyboardButton(text="🪙 Демо (серебро)", callback_data="bet_demo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="games_menu")]
    ])

def get_cube_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.add(InlineKeyboardButton(text=f"🎲 {i}", callback_data=f"cube_guess_{i}"))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="games_menu"))
    return builder.as_markup()

def get_roulette_multipliers() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mult in ROULETTE_MULTIPLIERS.keys():
        builder.add(InlineKeyboardButton(text=f"x{mult}", callback_data=f"roulette_{mult}"))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="games_menu"))
    return builder.as_markup()

def get_minesweeper_board(bombs: List[int], revealed: List[int], 
                          game_over: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(9):
        if i in revealed:
            text = "💔" if i in bombs else "💚"
        elif game_over and i in bombs:
            text = "❤️‍🩹"
        else:
            text = "🩵"
        callback = f"mine_{i}" if i not in revealed and not game_over else "mine_none"
        builder.add(InlineKeyboardButton(text=text, callback_data=callback))
    builder.adjust(3)
    if not game_over:
        builder.row(InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data="mine_cashout"))
    builder.row(InlineKeyboardButton(text="🚪 Выйти", callback_data="games_menu"))
    return builder.as_markup()

# ===== РЫНОК =====
def get_market_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Товары", callback_data="market_items")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_market_items_list(items: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.row(InlineKeyboardButton(
            text=f"🏷 {item['name']} — {item['price']} 💰",
            callback_data=f"market_item_{item['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="market_menu"))
    return builder.as_markup()

def get_market_item_buttons(item_id: int, can_buy: bool) -> InlineKeyboardMarkup:
    buttons = []
    if can_buy:
        buttons.append([InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_market_{item_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="market_items")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ТИММЕЙТЫ =====
def get_teams_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Анкеты игроков", callback_data="view_players")],
        [InlineKeyboardButton(text="🏰 Анкеты кланов", callback_data="view_clans")],
        [InlineKeyboardButton(text="📝 Создать анкету игрока (65 💰)", callback_data="create_player_profile")],
        [InlineKeyboardButton(text="🏰 Создать анкету клана (170 💰)", callback_data="create_clan_profile")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_profiles_list(profiles: List[Dict], profile_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in profiles[:10]:
        if profile_type == "player":
            text = f"👤 {p['nickname']} | {p['server']}"
            callback = f"view_player_{p['id']}"
        else:
            text = f"🏰 [{p['clan_tag']}] {p['clan_name']}"
            callback = f"view_clan_{p['id']}"
        builder.row(InlineKeyboardButton(text=text, callback_data=callback))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="teams_menu"))
    return builder.as_markup()

# ===== ПРОМОКОДЫ =====
def get_promo_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

# ===== АДМИН-ПАНЕЛЬ =====
def get_admin_panel(is_main: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="broadcast")],
        [InlineKeyboardButton(text="📦 Игровые заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="💳 Задание с картой", callback_data="create_card_task")],
        [
            InlineKeyboardButton(text="📋 Заявки", callback_data="pending_submissions"),
            InlineKeyboardButton(text="💸 Выводы", callback_data="withdraw_requests")
        ],
        [InlineKeyboardButton(text="📢 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="🛒 Управление рынком", callback_data="admin_market")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="manage_users")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
    ]
    
    if is_main:
        buttons.append([InlineKeyboardButton(text="👑 Управление админами", callback_data="manage_admins")])
        buttons.append([InlineKeyboardButton(text="🔄 Сбросить лидерборд", callback_data="reset_leaderboard")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_promos_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="list_promos")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])

def get_promos_list(promos: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in promos[:15]:
        status = "✅" if p['is_active'] else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{status} {p['code']} ({p['current_uses']}/{p['max_uses']})",
            callback_data=f"view_promo_{p['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promos"))
    return builder.as_markup()

def get_admin_market_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="create_market_item")],
        [InlineKeyboardButton(text="📋 Список товаров", callback_data="admin_market_list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])

def get_reward_type_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="reward_coins")],
        [InlineKeyboardButton(text="🎖 Привилегия", callback_data="reward_privilege")],
        [InlineKeyboardButton(text="🎁 Способность промокода", callback_data="reward_promo_ability")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_market")]
    ])

def get_privilege_select() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for priv_id, priv_data in PRIVILEGES.items():
        builder.row(InlineKeyboardButton(
            text=priv_data['name'],
            callback_data=f"set_priv_{priv_id}"
        ))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))
    return builder.as_markup()

def get_users_list(users: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users[:10]:
        name = u.get('username') or u.get('full_name') or str(u['user_id'])
        builder.row(InlineKeyboardButton(
            text=f"👤 {name[:20]}",
            callback_data=f"manage_user_{u['user_id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
    return builder.as_markup()

def get_user_manage_buttons(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data=f"change_bal_{user_id}")],
        [InlineKeyboardButton(text="🎖 Изменить привилегию", callback_data=f"change_priv_{user_id}")],
        [InlineKeyboardButton(text="🎬 Сделать ютубером", callback_data=f"make_youtuber_{user_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manage_users")]
    ])

def get_admins_list(admins: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for a in admins:
        icon = "👑" if a.get('is_main_admin') else "👤"
        name = a.get('username') or a.get('game_nick') or str(a['user_id'])
        builder.row(InlineKeyboardButton(
            text=f"{icon} {name}",
            callback_data=f"view_admin_{a['user_id']}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="add_admin"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
    return builder.as_markup()

def get_resource_categories() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, data in RESOURCES_CATEGORIES.items():
        builder.row(InlineKeyboardButton(
            text=f"{data['emoji']} {data['name']}",
            callback_data=f"category_{key}"
        ))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))
    return builder.as_markup()

def get_resource_items(category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    category_data = RESOURCES_CATEGORIES.get(category, {})
    for key, name in category_data.get('items', {}).items():
        builder.row(InlineKeyboardButton(text=name, callback_data=f"resource_{category}_{key}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="create_game_task"))
    return builder.as_markup()

def get_submissions_list(submissions: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in submissions[:10]:
        t = "🎮" if s['task_type'] == 'game' else "💳"
        builder.row(InlineKeyboardButton(
            text=f"{t} #{s['id']} | @{s.get('username') or 'Нет'}",
            callback_data=f"review_sub_{s['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
    return builder.as_markup()

def get_review_buttons(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{submission_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{submission_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="pending_submissions")]
    ])

def get_withdraw_list(withdrawals: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w in withdrawals[:10]:
        builder.row(InlineKeyboardButton(
            text=f"#{w['id']} | {w['coins']}💰 | @{w.get('username') or 'Нет'}",
            callback_data=f"review_wd_{w['id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
    return builder.as_markup()

def get_withdraw_review_buttons(wd_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выведено", callback_data=f"complete_wd_{wd_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_wd_{wd_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="withdraw_requests")]
    ])

def get_cancel_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])

def get_confirm_buttons(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="admin_panel")
        ]
    ])

# ===== ЗАКАЗЫ =====
def get_orders_list(orders: List[Dict], page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        category = RESOURCES_CATEGORIES.get(order['resource_category'], {})
        emoji = category.get('emoji', '📦')
        builder.row(InlineKeyboardButton(
            text=f"{emoji} #{order['id']} | {order['executor_reward']}💰",
            callback_data=f"view_order_{order['id']}"
        ))
    
    total_pages = math.ceil(total / TASKS_PER_PAGE)
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"open_orders_{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="none"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"open_orders_{page+1}"))
        builder.row(*nav)
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu"))
    return builder.as_markup()

def get_order_actions(order_id: int, is_creator: bool, is_executor: bool, 
                      status: str) -> InlineKeyboardMarkup:
    buttons = []
    
    if status == 'open' and not is_creator:
        buttons.append([InlineKeyboardButton(
            text="✅ Взять заказ", callback_data=f"take_order_{order_id}"
        )])
    
    if status == 'in_progress' and is_executor:
        buttons.append([InlineKeyboardButton(
            text="📸 Отправить доказательство", callback_data=f"submit_order_{order_id}"
        )])
    
    if status == 'pending_confirm' and is_creator:
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_order_{order_id}")
        ])
    
    if is_creator and status in ['open', 'in_progress']:
        buttons.append([InlineKeyboardButton(
            text="🚫 Отменить заказ", callback_data=f"cancel_order_{order_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_my_orders_list(orders: List[Dict], user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for order in orders[:10]:
        role = "📤" if order['creator_id'] == user_id else "📥"
        status_emoji = {
            'open': '🟢', 'in_progress': '🟡', 
            'pending_confirm': '🔵', 'completed': '✅', 'cancelled': '❌'
        }.get(order['status'], '❓')
        
        builder.row(InlineKeyboardButton(
            text=f"{role} #{order['id']} {status_emoji}",
            callback_data=f"view_order_{order['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_menu"))
    return builder.as_markup()

def get_admin_orders_list(orders: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for order in orders[:15]:
        status_emoji = {
            'open': '🟢', 'in_progress': '🟡', 
            'pending_confirm': '🔵', 'completed': '✅', 'cancelled': '❌'
        }.get(order['status'], '❓')
        
        builder.row(InlineKeyboardButton(
            text=f"#{order['id']} {status_emoji} | {order['total_reward']}💰",
            callback_data=f"admin_view_order_{order['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
    return builder.as_markup()

# ===== ПОДПИСКИ =====
def get_subscriptions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Доступные каналы", callback_data="sub_channels_list")],
        [InlineKeyboardButton(text="✅ Мои подписки", callback_data="my_subscriptions")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_channels_list(channels: List[Dict], user_subs: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for ch in channels:
        is_subbed = ch['channel_id'] in user_subs
        emoji = "✅" if is_subbed else "➕"
        action = "unsub" if is_subbed else "sub"
        
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {ch['channel_name']} (+1💰)",
            callback_data=f"{action}_{ch['channel_id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔄 Проверить подписки", callback_data="check_subscriptions"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="subscriptions_menu"))
    return builder.as_markup()

def get_admin_subscriptions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_sub_channel")],
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="list_sub_channels")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])

def get_sub_channels_admin_list(channels: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for ch in channels:
        builder.row(InlineKeyboardButton(
            text=f"{'📢' if ch['channel_type'] == 'channel' else '🤖'} {ch['channel_name']}",
            callback_data=f"manage_sub_ch_{ch['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscriptions"))
    return builder.as_markup()

# ===== РАССЫЛКА =====
def get_broadcast_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")
        ]
    ])
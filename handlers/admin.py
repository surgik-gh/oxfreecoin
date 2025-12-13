from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import RESOURCES_CATEGORIES, PRIVILEGES, WITHDRAW_PACKS

from states import (
    CreateGameTask, CreateCardTask, AddAdmin, UpdateAdminProfile,
    RejectSubmission, RejectWithdraw, CreatePromo, ManageUser, 
    CreateMarketItem, Broadcast, AddSubscriptionChannel
)

router = Router()

# ===== ФИЛЬТР =====
async def admin_check(callback: CallbackQuery) -> bool:
    return await db.is_admin(callback.from_user.id)

# ===== АДМИН-ПАНЕЛЬ =====
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.clear()
    is_main = await db.is_main_admin(callback.from_user.id)
    stats = await db.get_stats()
    
    text = f"""
⚙️ <b>Админ-панель</b>

👥 Пользователей: {stats['total_users']} ({stats['registered_users']} рег.)
📋 Заданий: {stats['active_game_tasks']} игр. / {stats['active_card_tasks']} карт.
🟡 На проверке: {stats['pending_submissions']} заявок
💸 Выводов: {stats['pending_withdrawals']}
"""
    await callback.message.edit_text(text, reply_markup=kb.get_admin_panel(is_main), parse_mode="HTML")
    await callback.answer()

# ===== СОЗДАНИЕ ИГРОВОГО ЗАДАНИЯ =====
@router.callback_query(F.data == "create_game_task")
async def create_game_task(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(CreateGameTask.category)
    await callback.message.edit_text(
        "➕ <b>Создание задания</b>\n\nВыберите категорию:",
        reply_markup=kb.get_resource_categories(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(CreateGameTask.category, F.data.startswith("category_"))
async def task_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("category_", "")
    await state.update_data(category=category)
    await state.set_state(CreateGameTask.resource)
    await callback.message.edit_text(
        "Выберите ресурс:",
        reply_markup=kb.get_resource_items(category)
    )
    await callback.answer()

@router.callback_query(CreateGameTask.resource, F.data.startswith("resource_"))
async def task_resource(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    resource = parts[-1]
    await state.update_data(resource=resource)
    await state.set_state(CreateGameTask.amount)
    await callback.message.edit_text(
        "Введите количество:",
        reply_markup=kb.get_cancel_button()
    )
    await callback.answer()

@router.message(CreateGameTask.amount)
async def task_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    await state.update_data(amount=amount)
    admin = await db.get_admin(message.from_user.id)
    
    if admin and admin.get('server_name') and admin.get('clan_name') and admin.get('game_nick'):
        await state.update_data(
            server=admin['server_name'],
            clan=admin['clan_name'],
            nick=admin['game_nick']
        )
        await state.set_state(CreateGameTask.description)
        await message.answer(
            f"📍 Данные из профиля:\n{admin['server_name']} | [{admin['clan_name']}] {admin['game_nick']}\n\n"
            "Описание (или '-' чтобы пропустить):",
            reply_markup=kb.get_cancel_button()
        )
    else:
        await state.set_state(CreateGameTask.server)
        await message.answer(
            "Введите данные:\n<code>Сервер | Клан | Ник</code>",
            reply_markup=kb.get_cancel_button(),
            parse_mode="HTML"
        )

@router.message(CreateGameTask.server)
async def task_server(message: Message, state: FSMContext):
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("⚠️ Формат: Сервер | Клан | Ник")
        return
    
    server, clan, nick = [p.strip() for p in parts]
    await state.update_data(server=server, clan=clan, nick=nick)
    await state.set_state(CreateGameTask.description)
    await message.answer("Описание (или '-'):", reply_markup=kb.get_cancel_button())

@router.message(CreateGameTask.description)
async def task_description(message: Message, state: FSMContext):
    desc = message.text if message.text != "-" else ""
    await state.update_data(description=desc)
    await state.set_state(CreateGameTask.reward)
    await message.answer("Награда (монеты):", reply_markup=kb.get_cancel_button())

@router.message(CreateGameTask.reward)
async def task_reward(message: Message, state: FSMContext):
    try:
        reward = int(message.text.replace(" ", "").replace(",", ""))
        if reward <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    data = await state.get_data()
    task_id = await db.create_game_task(
        message.from_user.id,
        data['server'], data['clan'], data['nick'],
        data['category'], data['resource'], data['amount'],
        reward, data.get('description', '')
    )
    await state.clear()
    
    await message.answer(
        f"✅ <b>Задание #{task_id} создано!</b>",
        reply_markup=kb.get_admin_panel(await db.is_main_admin(message.from_user.id)),
        parse_mode="HTML"
    )

# ===== СОЗДАНИЕ ЗАДАНИЯ С КАРТОЙ =====
@router.callback_query(F.data == "create_card_task")
async def create_card_task(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(CreateCardTask.name)
    await callback.message.edit_text(
        "💳 <b>Задание с картой</b>\n\nНазвание карты:",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CreateCardTask.name)
async def card_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CreateCardTask.link)
    await message.answer("🔗 Реферальная ссылка:")

@router.message(CreateCardTask.link)
async def card_link(message: Message, state: FSMContext):
    if not message.text.startswith(("http://", "https://")):
        await message.answer("⚠️ Ссылка должна начинаться с http(s)://")
        return
    await state.update_data(link=message.text)
    await state.set_state(CreateCardTask.description)
    await message.answer("📝 Описание:")

@router.message(CreateCardTask.description)
async def card_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateCardTask.reward)
    await message.answer("💰 Награда (монеты):")

@router.message(CreateCardTask.reward)
async def card_reward(message: Message, state: FSMContext):
    try:
        reward = int(message.text)
        if reward <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    data = await state.get_data()
    task_id = await db.create_card_task(
        message.from_user.id,
        data['name'], data['link'], data['description'], reward
    )
    await state.clear()
    
    await message.answer(
        f"✅ <b>Задание #{task_id} создано!</b>",
        reply_markup=kb.get_admin_panel(await db.is_main_admin(message.from_user.id)),
        parse_mode="HTML"
    )

# ===== ПРОВЕРКА ЗАЯВОК =====
@router.callback_query(F.data == "pending_submissions")
async def pending_submissions(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    subs = await db.get_pending_submissions()
    
    if not subs:
        text = "📋 <b>Заявки</b>\n\n✅ Нет заявок"
        markup = kb.get_back_button("admin_panel")
    else:
        text = f"📋 <b>Заявки</b>\n\nОжидают: {len(subs)}"
        markup = kb.get_submissions_list(subs)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("review_sub_"))
async def review_submission(callback: CallbackQuery, bot: Bot):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    sub_id = int(callback.data.split("_")[-1])
    sub = await db.get_submission(sub_id)
    
    if not sub:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    
    if sub['task_type'] == 'game':
        task = await db.get_game_task(sub['task_id'])
        task_info = f"🎮 #{task['id']}" if task else "🎮 Игровое"
        reward = task.get('reward', 0) if task else 0
    else:
        task = await db.get_card_task(sub['task_id'])
        task_info = f"💳 {task['card_name']}" if task else "💳 Карта"
        reward = task.get('reward', 0) if task else 0
    
    text = f"""
🔍 <b>Заявка #{sub['id']}</b>

👤 {sub['full_name']} (@{sub.get('username') or 'нет'})
📋 {task_info}
💰 Награда: {reward}
"""
    await callback.message.edit_text(text, parse_mode="HTML")
    await bot.send_photo(
        callback.message.chat.id,
        sub['proof_file_id'],
        reply_markup=kb.get_review_buttons(sub_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_submission(callback: CallbackQuery, bot: Bot):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    sub_id = int(callback.data.split("_")[-1])
    sub = await db.approve_submission(sub_id, callback.from_user.id)
    
    if not sub:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    
    await db.update_balance(sub['user_id'], sub['reward'], f"Задание #{sub['task_id']}")
    await db.increment_completed_tasks(sub['user_id'])
    
    try:
        await bot.send_message(
            sub['user_id'],
            f"✅ <b>Заявка #{sub['id']} одобрена!</b>\n💰 +{sub['reward']} монет",
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Заявка #{sub_id} одобрена!",
        reply_markup=kb.get_back_button("pending_submissions")
    )
    await callback.answer("✅ Одобрено!")

@router.callback_query(F.data.startswith("reject_"))
async def reject_start(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("reject_wd_"):
        return  # Обрабатывается отдельно
    
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    sub_id = int(callback.data.split("_")[-1])
    await state.set_state(RejectSubmission.comment)
    await state.update_data(sub_id=sub_id)
    
    await callback.message.delete()
    await callback.message.answer(
        "❌ Введите причину отклонения:",
        reply_markup=kb.get_cancel_button()
    )
    await callback.answer()

@router.message(RejectSubmission.comment)
async def reject_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    sub = await db.reject_submission(data['sub_id'], message.from_user.id, message.text)
    await state.clear()
    
    if sub:
        try:
            await bot.send_message(
                sub['user_id'],
                f"❌ <b>Заявка #{sub['id']} отклонена</b>\n\n💬 {message.text}",
                parse_mode="HTML"
            )
        except:
            pass
    
    await message.answer(
        "❌ Заявка отклонена",
        reply_markup=kb.get_back_button("pending_submissions")
    )

# ===== ЗАЯВКИ НА ВЫВОД =====
@router.callback_query(F.data == "withdraw_requests")
async def withdraw_requests(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    wds = await db.get_pending_withdrawals()
    
    if not wds:
        text = "💸 <b>Выводы</b>\n\n✅ Нет заявок"
        markup = kb.get_back_button("admin_panel")
    else:
        text = f"💸 <b>Выводы</b>\n\nОжидают: {len(wds)}"
        markup = kb.get_withdraw_list(wds)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("review_wd_"))
async def review_withdraw(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    wd_id = int(callback.data.split("_")[-1])
    wd = await db.get_withdrawal(wd_id)
    
    if not wd:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    
    pack = WITHDRAW_PACKS.get(wd['pack_id'], {})
    
    text = f"""
💸 <b>Вывод #{wd['id']}</b>

👤 {wd['full_name']} (@{wd.get('username') or 'нет'})
💰 {wd['coins']} монет
📦 {pack.get('name', wd['pack_id'])}
🎮 ID: <code>{wd['game_id']}</code>
"""
    await callback.message.edit_text(
        text, 
        reply_markup=kb.get_withdraw_review_buttons(wd_id), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("complete_wd_"))
async def complete_withdraw(callback: CallbackQuery, bot: Bot):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    wd_id = int(callback.data.split("_")[-1])
    wd = await db.complete_withdrawal(wd_id, callback.from_user.id)
    
    if not wd:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    
    try:
        await bot.send_message(
            wd['user_id'],
            f"✅ <b>Вывод #{wd['id']} выполнен!</b>\n💰 {wd['coins']} монет",
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.answer("✅ Выполнено!", show_alert=True)
    
    # Обновляем список
    wds = await db.get_pending_withdrawals()
    if not wds:
        text = "💸 <b>Выводы</b>\n\n✅ Нет заявок"
        markup = kb.get_back_button("admin_panel")
    else:
        text = f"💸 <b>Выводы</b>\n\nОжидают: {len(wds)}"
        markup = kb.get_withdraw_list(wds)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("reject_wd_"))
async def reject_wd_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    wd_id = int(callback.data.split("_")[-1])
    await state.set_state(RejectWithdraw.reason)
    await state.update_data(wd_id=wd_id)
    
    await callback.message.edit_text(
        "❌ Введите причину отказа:\n<i>(монеты вернутся)</i>",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(RejectWithdraw.reason)
async def reject_wd_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    wd = await db.reject_withdrawal(data['wd_id'], message.from_user.id, message.text)
    await state.clear()
    
    if wd:
        try:
            await bot.send_message(
                wd['user_id'],
                f"❌ <b>Вывод #{wd['id']} отклонён</b>\n\n"
                f"💬 {message.text}\n💵 Монеты возвращены",
                parse_mode="HTML"
            )
        except:
            pass
    
    await message.answer("❌ Отклонено, монеты возвращены", reply_markup=kb.get_back_button("withdraw_requests"))

# ===== ПРОМОКОДЫ =====
@router.callback_query(F.data == "admin_promos")
async def admin_promos(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎁 <b>Промокоды</b>",
        reply_markup=kb.get_admin_promos_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "create_promo")
async def create_promo(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(CreatePromo.code)
    await callback.message.edit_text(
        "🎁 <b>Создание промокода</b>\n\n"
        "Введите код (или 'auto' для автогенерации):",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CreatePromo.code)
async def promo_code(message: Message, state: FSMContext):
    code = message.text.upper()
    if code == "AUTO":
        code = db.generate_promo_code()
    
    existing = await db.get_promocode(code)
    if existing:
        await message.answer("⚠️ Такой код уже существует")
        return
    
    await state.update_data(code=code)
    await state.set_state(CreatePromo.coins)
    await message.answer(f"Код: <code>{code}</code>\n\nСколько монет за активацию?", parse_mode="HTML")

@router.message(CreatePromo.coins)
async def promo_coins(message: Message, state: FSMContext):
    try:
        coins = int(message.text)
        if coins <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    await state.update_data(coins=coins)
    await state.set_state(CreatePromo.uses)
    await message.answer("Сколько активаций?")

@router.message(CreatePromo.uses)
async def promo_uses(message: Message, state: FSMContext):
    try:
        uses = int(message.text)
        if uses <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    data = await state.get_data()
    await db.create_promocode(data['code'], data['coins'], uses, message.from_user.id)
    await state.clear()
    
    await message.answer(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎁 <code>{data['code']}</code>\n"
        f"💰 {data['coins']} монет × {uses} активаций",
        reply_markup=kb.get_back_button("admin_promos"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "list_promos")
async def list_promos(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    promos = await db.get_all_promocodes()
    
    if not promos:
        text = "📋 <b>Промокоды</b>\n\nПусто"
        markup = kb.get_back_button("admin_promos")
    else:
        text = f"📋 <b>Промокоды</b>\n\nВсего: {len(promos)}"
        markup = kb.get_promos_list(promos)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

# ===== УПРАВЛЕНИЕ РЫНКОМ =====
@router.callback_query(F.data == "admin_market")
async def admin_market(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🛒 <b>Управление рынком</b>",
        reply_markup=kb.get_admin_market_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "create_market_item")
async def create_market_item(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(CreateMarketItem.name)
    await callback.message.edit_text(
        "🏷 <b>Создание товара</b>\n\nНазвание:",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CreateMarketItem.name)
async def market_item_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CreateMarketItem.price)
    await message.answer("💰 Цена (монеты):")

@router.message(CreateMarketItem.price)
async def market_item_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    await state.update_data(price=price)
    await state.set_state(CreateMarketItem.description)
    await message.answer("📝 Описание:")

@router.message(CreateMarketItem.description)
async def market_item_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateMarketItem.reward_type)
    await message.answer("Тип награды:", reply_markup=kb.get_reward_type_menu())

@router.callback_query(CreateMarketItem.reward_type, F.data.startswith("reward_"))
async def market_item_reward_type(callback: CallbackQuery, state: FSMContext):
    reward_type = callback.data.replace("reward_", "")
    await state.update_data(reward_type=reward_type)
    await state.set_state(CreateMarketItem.reward_value)
    
    if reward_type == "coins":
        prompt = "Сколько монет?"
    elif reward_type == "privilege":
        prompt = "Какая привилегия? (newbie/trainee/strong/youtuber)"
    else:
        prompt = "Сколько промокодов можно создать?"
    
    await callback.message.edit_text(prompt, reply_markup=kb.get_cancel_button())
    await callback.answer()

@router.message(CreateMarketItem.reward_value)
async def market_item_reward_value(message: Message, state: FSMContext):
    data = await state.get_data()
    
    await db.create_market_item(
        data['name'], data['price'], data['description'],
        data['reward_type'], message.text
    )
    await state.clear()
    
    await message.answer(
        "✅ <b>Товар создан!</b>",
        reply_markup=kb.get_back_button("admin_market"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_market_list")
async def admin_market_list(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    items = await db.get_market_items()
    
    if not items:
        text = "📋 <b>Товары</b>\n\nПусто"
        markup = kb.get_back_button("admin_market")
    else:
        text = f"📋 <b>Товары на рынке</b>\n\nВсего: {len(items)}"
        markup = kb.get_market_items_list(items)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

# ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====
@router.callback_query(F.data == "manage_users")
async def manage_users(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(ManageUser.search)
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Введите @username, ID или имя для поиска:",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ManageUser.search)
async def search_user(message: Message, state: FSMContext):
    query = message.text.replace("@", "")
    users = await db.search_users(query)
    
    if not users:
        await message.answer("❌ Никого не найдено")
        return
    
    await state.clear()
    await message.answer(
        f"👥 Найдено: {len(users)}",
        reply_markup=kb.get_users_list(users)
    )

@router.callback_query(F.data.startswith("manage_user_"))
async def view_user(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    user = await db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    
    priv = PRIVILEGES.get(user['privilege'], PRIVILEGES['newbie'])
    
    text = f"""
👤 <b>Пользователь</b>

🆔 ID: <code>{user['user_id']}</code>
📱 @{user.get('username') or 'нет'}
📛 {user['full_name']}
🎖 {priv['name']}

💰 Баланс: {user['balance']}
🪙 Демо: {user['demo_balance']}
📈 Заработано: {user['total_earned']}
"""
    await callback.message.edit_text(
        text, 
        reply_markup=kb.get_user_manage_buttons(user_id), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("change_bal_"))
async def change_balance_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    await state.set_state(ManageUser.balance_change)
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "💰 Введите сумму (+ или -):\n"
        "Например: +100 или -50",
        reply_markup=kb.get_cancel_button()
    )
    await callback.answer()

@router.message(ManageUser.balance_change)
async def change_balance(message: Message, state: FSMContext):
    try:
        amount = int(message.text.replace(" ", ""))
    except:
        await message.answer("⚠️ Введите число")
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    await db.update_balance(user_id, amount, f"Изменено админом {message.from_user.id}")
    await state.clear()
    
    await message.answer(
        f"✅ Баланс изменён на {amount:+}",
        reply_markup=kb.get_back_button("manage_users")
    )

@router.callback_query(F.data.startswith("change_priv_"))
async def change_privilege_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "🎖 Выберите привилегию:",
        reply_markup=kb.get_privilege_select()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_priv_"))
async def set_privilege(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    priv = callback.data.replace("set_priv_", "")
    data = await state.get_data()
    user_id = data.get('target_user_id')
    
    if user_id:
        await db.set_user_privilege(user_id, priv)
        await state.clear()
        priv_name = PRIVILEGES.get(priv, {}).get('name', priv)
        await callback.message.edit_text(
            f"✅ Привилегия изменена на {priv_name}",
            reply_markup=kb.get_back_button("manage_users")
        )
    await callback.answer()

@router.callback_query(F.data.startswith("make_youtuber_"))
async def make_youtuber(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    await db.set_user_privilege(user_id, "youtuber")
    
    await callback.answer("✅ Теперь ютубер!", show_alert=True)
    await callback.message.edit_text(
        "✅ Пользователь теперь ютубер!",
        reply_markup=kb.get_back_button("manage_users")
    )

# ===== СБРОС ЛИДЕРБОРДА =====
@router.callback_query(F.data == "reset_leaderboard")
async def reset_leaderboard_confirm(callback: CallbackQuery):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚠️ <b>Сбросить лидерборд?</b>\n\n"
        "Все показатели 'Заработано' обнулятся!",
        reply_markup=kb.get_confirm_buttons("reset_lb"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_reset_lb")
async def confirm_reset_lb(callback: CallbackQuery):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await db.reset_leaderboard()
    await callback.message.edit_text(
        "✅ <b>Лидерборд сброшен!</b>",
        reply_markup=kb.get_admin_panel(True),
        parse_mode="HTML"
    )
    await callback.answer("✅ Сброшено!")

# ===== УПРАВЛЕНИЕ АДМИНАМИ =====
@router.callback_query(F.data == "manage_admins")
async def manage_admins(callback: CallbackQuery):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    admins = await db.get_all_admins()
    await callback.message.edit_text(
        f"👑 <b>Администраторы</b>\n\nВсего: {len(admins)}",
        reply_markup=kb.get_admins_list(admins),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_admin_"))
async def view_admin(callback: CallbackQuery):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    admin_id = int(callback.data.split("_")[-1])
    admin = await db.get_admin(admin_id)
    
    if not admin:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    
    is_main = admin.get('is_main_admin', False)
    role = "👑 Главный админ" if is_main else "👤 Администратор"
    
    text = f"""
{role}

🆔 ID: <code>{admin['user_id']}</code>
📱 @{admin.get('username') or 'нет'}
🌐 Сервер: {admin.get('server_name') or 'не указан'}
👥 Клан: [{admin.get('clan_name') or '?'}]
🎮 Ник: {admin.get('game_nick') or 'не указан'}
"""
    
    buttons = []
    if not is_main:
        buttons.append([InlineKeyboardButton(text="❌ Удалить", callback_data=f"remove_admin_{admin_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="manage_admins")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remove_admin_"))
async def remove_admin(callback: CallbackQuery, bot: Bot):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    admin_id = int(callback.data.split("_")[-1])
    success = await db.remove_admin(admin_id)
    
    if success:
        try:
            await bot.send_message(admin_id, "⚠️ Вы больше не администратор.")
        except:
            pass
        await callback.answer("✅ Удалён", show_alert=True)
    else:
        await callback.answer("❌ Нельзя удалить главного", show_alert=True)
    
    admins = await db.get_all_admins()
    await callback.message.edit_text(
        f"👑 <b>Администраторы</b>\n\nВсего: {len(admins)}",
        reply_markup=kb.get_admins_list(admins),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AddAdmin.user_id)
    await callback.message.edit_text(
        "➕ <b>Добавление админа</b>\n\nВведите Telegram ID:",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AddAdmin.user_id)
async def add_admin_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except:
        await message.answer("⚠️ Введите число")
        return
    
    if await db.is_admin(user_id):
        await message.answer("⚠️ Уже админ")
        return
    
    await state.update_data(user_id=user_id)
    await state.set_state(AddAdmin.server)
    await message.answer("🌐 Сервер:")

@router.message(AddAdmin.server)
async def add_admin_server(message: Message, state: FSMContext):
    await state.update_data(server=message.text)
    await state.set_state(AddAdmin.clan)
    await message.answer("👥 Клан:")

@router.message(AddAdmin.clan)
async def add_admin_clan(message: Message, state: FSMContext):
    await state.update_data(clan=message.text)
    await state.set_state(AddAdmin.nick)
    await message.answer("🎮 Ник:")

@router.message(AddAdmin.nick)
async def add_admin_nick(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    
    try:
        chat = await bot.get_chat(data['user_id'])
        username = chat.username
    except:
        username = None
    
    await db.add_admin(data['user_id'], username, data['clan'], message.text, data['server'])
    await state.clear()
    
    try:
        await bot.send_message(data['user_id'], "🎉 Вы назначены администратором!")
    except:
        pass
    
    await message.answer("✅ Админ добавлен!", reply_markup=kb.get_back_button("manage_admins"))

# ===== СТАТИСТИКА =====
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    stats = await db.get_stats()
    
    text = f"""
📊 <b>Статистика</b>

👥 Пользователей: {stats['total_users']}
✅ Зарегистрировано: {stats['registered_users']}

🎮 Игровых заданий: {stats['active_game_tasks']}
💳 Заданий с картами: {stats['active_card_tasks']}

📋 Заявок: {stats['pending_submissions']}
💸 Выводов: {stats['pending_withdrawals']}
✅ Выполнено: {stats['total_completed']}

💰 Общий баланс: {stats['total_balance']:,}
🎁 Промокодов: {stats['active_promos']}
"""
    await callback.message.edit_text(
        text, 
        reply_markup=kb.get_back_button("admin_panel"), 
        parse_mode="HTML"
    )
    await callback.answer()

# ===== РАССЫЛКА =====
@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(Broadcast.message)
    await callback.message.edit_text(
        "📢 <b>Рассылка всем пользователям</b>\n\n"
        "Отправьте сообщение для рассылки.\n"
        "Можно отправить текст, фото или фото с текстом.",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(Broadcast.message, F.text)
async def broadcast_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text, photo=None)
    await state.set_state(Broadcast.confirm)
    
    await message.answer(
        f"📢 <b>Предпросмотр:</b>\n\n{message.text}\n\n"
        f"Отправить всем?",
        reply_markup=kb.get_broadcast_confirm(),
        parse_mode="HTML"
    )

@router.message(Broadcast.message, F.photo)
async def broadcast_photo(message: Message, state: FSMContext):
    await state.update_data(
        text=message.caption or "",
        photo=message.photo[-1].file_id
    )
    await state.set_state(Broadcast.confirm)
    
    await message.answer_photo(
        message.photo[-1].file_id,
        caption=f"📢 <b>Предпросмотр:</b>\n\n{message.caption or ''}\n\nОтправить всем?",
        reply_markup=kb.get_broadcast_confirm(),
        parse_mode="HTML"
    )

@router.callback_query(Broadcast.confirm, F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    
    user_ids = await db.get_all_user_ids()
    
    await callback.message.edit_text("📤 Начинаю рассылку...")
    
    success = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            if data.get('photo'):
                await bot.send_photo(user_id, data['photo'], caption=data.get('text', ''))
            else:
                await bot.send_message(user_id, data['text'])
            success += 1
        except:
            failed += 1
        
        # Задержка чтобы не забанили
        if success % 30 == 0:
            import asyncio
            await asyncio.sleep(1)
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"✅ Доставлено: {success}\n"
        f"❌ Не доставлено: {failed}",
        reply_markup=kb.get_back_button("admin_panel"),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== ИГРОВЫЕ ЗАКАЗЫ (для админа) =====
@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    orders = await db.get_all_orders_admin()
    
    if not orders:
        text = "📦 <b>Игровые заказы</b>\n\nПока нет заказов"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("admin_panel"), parse_mode="HTML")
    else:
        text = f"📦 <b>Игровые заказы</b>\n\nВсего: {len(orders)}"
        await callback.message.edit_text(text, reply_markup=kb.get_admin_orders_list(orders), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_order_"))
async def admin_view_order(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[-1])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    
    status_text = {
        'open': '🟢 Открыт',
        'in_progress': '🟡 Выполняется',
        'pending_confirm': '🔵 Ожидает подтверждения',
        'completed': '✅ Выполнен',
        'cancelled': '❌ Отменён'
    }.get(order['status'], order['status'])
    
    executor = f"@{order['executor_username']}" if order.get('executor_username') else "—"
    
    text = f"""
📦 <b>Игровой заказ #{order['id']}</b>

📊 Статус: {status_text}

━━━━━━━━━━━━━━━━━━

👤 Заказчик: @{order.get('creator_username') or 'скрыт'}
🔧 Выполняет: {executor}

💰 Всего монет: {order['total_reward']}
💵 С комиссией: {order['executor_reward']} <i>(комиссия {int(TASK_COMMISSION*100)}%)</i>

📅 Создан: {str(order['created_at'])[:16]}
"""
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_back_button("admin_orders"),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== УПРАВЛЕНИЕ ПОДПИСКАМИ =====
@router.callback_query(F.data == "admin_subscriptions")
async def admin_subscriptions(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Управление подписками</b>",
        reply_markup=kb.get_admin_subscriptions_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "add_sub_channel")
async def add_sub_channel(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AddSubscriptionChannel.channel_id)
    await callback.message.edit_text(
        "➕ <b>Добавление канала</b>\n\n"
        "Введите ID канала (например: @channel_name):",
        reply_markup=kb.get_cancel_button(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AddSubscriptionChannel.channel_id)
async def sub_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    if not channel_id.startswith("@"):
        channel_id = "@" + channel_id
    
    await state.update_data(channel_id=channel_id)
    await state.set_state(AddSubscriptionChannel.channel_name)
    await message.answer("Введите название канала:")

@router.message(AddSubscriptionChannel.channel_name)
async def sub_channel_name(message: Message, state: FSMContext):
    data = await state.get_data()
    
    await db.add_subscription_channel(data['channel_id'], message.text)
    await state.clear()
    
    await message.answer(
        f"✅ <b>Канал добавлен!</b>\n\n"
        f"📢 {data['channel_id']} — {message.text}",
        reply_markup=kb.get_back_button("admin_subscriptions"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "list_sub_channels")
async def list_sub_channels(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    channels = await db.get_subscription_channels()
    
    if not channels:
        text = "📋 <b>Каналы</b>\n\nПусто"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("admin_subscriptions"), parse_mode="HTML")
    else:
        text = f"📋 <b>Каналы для подписки</b>\n\nВсего: {len(channels)}"
        await callback.message.edit_text(text, reply_markup=kb.get_sub_channels_admin_list(channels), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("manage_sub_ch_"))
async def manage_sub_channel(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    ch_id = int(callback.data.split("_")[-1])
    channels = await db.get_subscription_channels()
    channel = next((c for c in channels if c['id'] == ch_id), None)
    
    if not channel:
        await callback.answer("❌ Не найден", show_alert=True)
        return
    
    text = f"""
📢 <b>{channel['channel_name']}</b>

🆔 ID: {channel['channel_id']}
📅 Добавлен: {str(channel['created_at'])[:10]}
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_sub_ch_{channel['channel_id']}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="list_sub_channels")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("del_sub_ch_"))
async def delete_sub_channel(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    channel_id = callback.data.replace("del_sub_ch_", "")
    await db.remove_subscription_channel(channel_id)
    
    await callback.answer("✅ Удалён", show_alert=True)
    
    channels = await db.get_subscription_channels()
    if not channels:
        text = "📋 <b>Каналы</b>\n\nПусто"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("admin_subscriptions"), parse_mode="HTML")
    else:
        text = f"📋 <b>Каналы</b>\n\nВсего: {len(channels)}"
        await callback.message.edit_text(text, reply_markup=kb.get_sub_channels_admin_list(channels), parse_mode="HTML")
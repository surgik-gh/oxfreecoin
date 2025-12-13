from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
import random

import database as db
import keyboards as kb
from config import (
    CAPTCHA_EMOJIS, PRIVILEGES, WITHDRAW_PACKS, 
    STARS_PER_COIN, TELEGRAM_CHANNEL
)
from states import Registration, WithdrawMoney, EnterPromo, YouTuberPromo

router = Router()

# ===== СТАРТ И КАПЧА =====
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await db.create_user(
            message.from_user.id,
            message.from_user.username or "",
            message.from_user.full_name or ""
        )
        user = await db.get_user(message.from_user.id)
    
    # Если не зарегистрирован - капча
    if not user['is_registered']:
        correct = random.choice(CAPTCHA_EMOJIS)
        others = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 4)
        all_emojis = [correct] + others
        random.shuffle(all_emojis)
        
        await state.set_state(Registration.captcha)
        await state.update_data(correct_emoji=correct)
        
        text = f"""
🤖 <b>Проверка на робота</b>

Выберите этот смайлик: {correct}
"""
        await message.answer(text, reply_markup=kb.get_captcha_keyboard(correct, all_emojis), parse_mode="HTML")
        return
    
    # Обновляем привилегию по дням
    await db.update_user_privilege_by_days(message.from_user.id)
    
    is_admin = await db.is_admin(message.from_user.id)
    priv = PRIVILEGES.get(user['privilege'], PRIVILEGES['newbie'])
    
    text = f"""
🎮 <b>Oxide Coins Bot</b>

Привет, {priv['name']} <b>{message.from_user.full_name}</b>!

💰 Баланс: <b>{user['balance']:,}</b> монет
🪙 Демо: <b>{user['demo_balance']:,}</b> серебра

Выбери действие:
"""
    await message.answer(text, reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML")

@router.callback_query(F.data.startswith("captcha_"))
async def check_captcha(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = callback.data.replace("captcha_", "")
    
    if selected == data.get('correct_emoji'):
        await state.set_state(Registration.server)
        await callback.message.edit_text(
            "✅ <b>Верно!</b>\n\n📝 Теперь давай заполним профиль.\n\n"
            "🌐 На каком сервере ты чаще всего играешь?",
            parse_mode="HTML"
        )
    else:
        correct = random.choice(CAPTCHA_EMOJIS)
        others = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 4)
        all_emojis = [correct] + others
        random.shuffle(all_emojis)
        
        await state.update_data(correct_emoji=correct)
        await callback.message.edit_text(
            f"❌ Неверно! Попробуй ещё раз.\n\nВыбери: {correct}",
            reply_markup=kb.get_captcha_keyboard(correct, all_emojis)
        )
    await callback.answer()

@router.message(Registration.server)
async def reg_server(message: Message, state: FSMContext):
    await state.update_data(server=message.text)
    await state.set_state(Registration.nickname)
    await message.answer("👤 Введи свой игровой никнейм:")

@router.message(Registration.nickname)
async def reg_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(Registration.avatar)
    await message.answer(
        "🖼 Отправь аватарку (фото) или нажми пропустить:",
        reply_markup=kb.get_skip_button("description")
    )

@router.callback_query(Registration.avatar, F.data == "skip_description")
async def skip_avatar(callback: CallbackQuery, state: FSMContext):
    await state.update_data(avatar=None)
    await state.set_state(Registration.description)
    await callback.message.edit_text(
        "📝 Напиши немного о себе (или пропусти):",
        reply_markup=kb.get_skip_button("finish")
    )
    await callback.answer()

@router.message(Registration.avatar, F.photo)
async def reg_avatar(message: Message, state: FSMContext):
    await state.update_data(avatar=message.photo[-1].file_id)
    await state.set_state(Registration.description)
    await message.answer(
        "📝 Напиши немного о себе (или пропусти):",
        reply_markup=kb.get_skip_button("finish")
    )

@router.message(Registration.avatar)
async def reg_avatar_wrong(message: Message):
    await message.answer("⚠️ Отправь фото или нажми пропустить")

@router.callback_query(Registration.description, F.data == "skip_finish")
async def skip_description(callback: CallbackQuery, state: FSMContext):
    await finish_registration(callback.message, state, callback.from_user.id)
    await callback.answer()

@router.message(Registration.description)
async def reg_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await finish_registration(message, state, message.from_user.id)

async def finish_registration(message: Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    await db.complete_registration(
        user_id,
        data.get('server', ''),
        data.get('nickname', ''),
        data.get('avatar'),
        data.get('description')
    )
    await state.clear()
    
    is_admin = await db.is_admin(user_id)
    await message.answer(
        "✅ <b>Регистрация завершена!</b>\n\nДобро пожаловать!",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== ГЛАВНОЕ МЕНЮ =====
@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    is_admin = await db.is_admin(callback.from_user.id)
    
    if user:
        await db.update_user_privilege_by_days(callback.from_user.id)
        priv = PRIVILEGES.get(user['privilege'], PRIVILEGES['newbie'])
        
        text = f"""
🎮 <b>Oxide Coins Bot</b>

{priv['name']} <b>{user['full_name']}</b>

💰 Баланс: <b>{user['balance']:,}</b> монет
🪙 Демо: <b>{user['demo_balance']:,}</b> серебра
"""
    else:
        text = "🎮 <b>Oxide Coins Bot</b>"
    
    await callback.message.edit_text(text, reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML")
    await callback.answer()

# ===== БАЛАНС =====
@router.callback_query(F.data == "my_balance")
async def my_balance(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    priv = PRIVILEGES.get(user['privilege'], PRIVILEGES['newbie'])
    withdrawals = await db.get_user_withdrawals(callback.from_user.id, 3)
    
    text = f"""
💰 <b>Ваш профиль</b>

👤 {user['full_name']}
🎖 {priv['name']}
🌐 Сервер: {user.get('game_server') or 'Не указан'}
🎮 Ник: {user.get('game_nickname') or 'Не указан'}

━━━━━━━━━━━━━━━━━━

💵 <b>Баланс:</b> {user['balance']:,} монет
🪙 <b>Демо:</b> {user['demo_balance']:,} серебра
📈 <b>Заработано:</b> {user['total_earned']:,} монет
✅ <b>Заданий:</b> {user['tasks_completed']}
"""
    
    if withdrawals:
        text += "\n━━━━━━━━━━━━━━━━━━\n📤 <b>Выводы:</b>\n"
        for w in withdrawals:
            st = {"pending": "🟡", "completed": "✅", "rejected": "❌"}.get(w['status'], "❓")
            text += f"• {st} {w['coins']} монет\n"
    
    is_youtuber = user['privilege'] in ['youtuber', 'admin']
    await callback.message.edit_text(
        text, 
        reply_markup=kb.get_balance_menu(is_youtuber), 
        parse_mode="HTML"
    )
    await callback.answer()

# ===== ВЫВОД =====
@router.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    balance = user['balance'] if user else 0
    
    text = f"""
💸 <b>Вывод монет</b>

💰 Баланс: <b>{balance:,}</b> монет

Выберите пак:
"""
    await callback.message.edit_text(text, reply_markup=kb.get_withdraw_packs(balance), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "not_enough")
async def not_enough(callback: CallbackQuery):
    await callback.answer("❌ Недостаточно монет!", show_alert=True)

@router.callback_query(F.data.startswith("withdraw_pack_"))
async def select_pack(callback: CallbackQuery, state: FSMContext):
    pack_id = callback.data.replace("withdraw_", "")
    pack = WITHDRAW_PACKS.get(pack_id)
    
    if not pack:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    user = await db.get_user(callback.from_user.id)
    if user['balance'] < pack['coins']:
        await callback.answer("❌ Недостаточно монет!", show_alert=True)
        return
    
    await state.set_state(WithdrawMoney.game_id)
    await state.update_data(pack_id=pack_id, coins=pack['coins'])
    
    await callback.message.edit_text(
        f"💸 <b>Вывод: {pack['name']}</b>\n\n"
        f"💰 Сумма: <b>{pack['coins']}</b> монет\n\n"
        "Введите ваш <b>Steam ID</b> или <b>игровой ник</b>:",
        reply_markup=kb.get_back_button("withdraw_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(WithdrawMoney.game_id)
async def process_withdraw(message: Message, state: FSMContext):
    game_id = message.text.strip()
    if len(game_id) < 2:
        await message.answer("⚠️ Введите корректный ID")
        return
    
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    
    if user['balance'] < data['coins']:
        await state.clear()
        await message.answer("❌ Недостаточно монет!")
        return
    
    await db.update_balance(message.from_user.id, -data['coins'], f"Вывод: {data['pack_id']}")
    req_id = await db.create_withdraw_request(message.from_user.id, data['pack_id'], data['coins'], game_id)
    await state.clear()
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        f"✅ <b>Заявка #{req_id} создана!</b>\n\n"
        f"💰 {data['coins']} монет\n"
        f"🎮 ID: <code>{game_id}</code>\n\n"
        "⏳ Ожидайте обработки.",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== ПОКУПКА МОНЕТ ЗА ЗВЁЗДЫ =====
@router.callback_query(F.data == "buy_coins")
async def buy_coins_menu(callback: CallbackQuery):
    text = f"""
⭐ <b>Покупка монет за Telegram Stars</b>

Курс: <b>{STARS_PER_COIN}</b> звёзд = 1 монета

Выберите пакет:
"""
    await callback.message.edit_text(text, reply_markup=kb.get_buy_coins_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "buy_stars_10")
async def buy_stars_10(callback: CallbackQuery, bot: Bot):
    await send_stars_invoice(callback, bot, 10)

@router.callback_query(F.data == "buy_stars_50")
async def buy_stars_50(callback: CallbackQuery, bot: Bot):
    await send_stars_invoice(callback, bot, 50)

@router.callback_query(F.data == "buy_stars_100")
async def buy_stars_100(callback: CallbackQuery, bot: Bot):
    await send_stars_invoice(callback, bot, 100)

@router.callback_query(F.data == "buy_stars_500")
async def buy_stars_500(callback: CallbackQuery, bot: Bot):
    await send_stars_invoice(callback, bot, 500)

async def send_stars_invoice(callback: CallbackQuery, bot: Bot, coins: int):
    """Отправка счёта на оплату звёздами"""
    from aiogram.types import LabeledPrice
    
    stars_amount = coins * STARS_PER_COIN
    
    await callback.message.delete()
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"💰 {coins} монет",
        description=f"Покупка {coins} монет для Oxide Coins Bot",
        payload=f"buy_coins_{coins}",
        provider_token="",  # Пустой для Stars
        currency="XTR",  # Валюта Telegram Stars
        prices=[LabeledPrice(label=f"{coins} монет", amount=stars_amount)],
        start_parameter=f"buy_{coins}"
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query):
    """Подтверждение платежа"""
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты"""
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("buy_coins_"):
        coins = int(payload.replace("buy_coins_", ""))
        
        await db.update_balance(
            message.from_user.id, 
            coins, 
            f"Покупка за {message.successful_payment.total_amount} звёзд"
        )
        
        is_admin = await db.is_admin(message.from_user.id)
        
        await message.answer(
            f"✅ <b>Оплата успешна!</b>\n\n"
            f"💰 +{coins} монет зачислено на баланс!\n"
            f"⭐ Списано: {message.successful_payment.total_amount} звёзд",
            reply_markup=kb.get_main_menu(is_admin),
            parse_mode="HTML"
        )

# ===== ПРОМОКОД =====
@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EnterPromo.code)
    await callback.message.edit_text(
        "🎁 <b>Введите промокод:</b>",
        reply_markup=kb.get_back_button("main_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(EnterPromo.code)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    promo = await db.get_promocode(code)
    
    if not promo:
        await message.answer("❌ Промокод не найден или неактивен")
        return
    
    if promo['current_uses'] >= promo['max_uses']:
        await message.answer("❌ Промокод исчерпан")
        return
    
    success = await db.use_promocode(message.from_user.id, promo['id'])
    if not success:
        await message.answer("❌ Вы уже использовали этот промокод")
        return
    
    await db.update_balance(message.from_user.id, promo['coins'], f"Промокод: {code}")
    await state.clear()
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"💰 +{promo['coins']} монет",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== ЮТУБЕР ПРОМОКОД =====
@router.callback_query(F.data == "youtuber_promo")
async def youtuber_promo(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    
    if user['privilege'] not in ['youtuber', 'admin']:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if user['balance'] < 10:
        await callback.answer("❌ Минимум 10 монет на балансе", show_alert=True)
        return
    
    await state.set_state(YouTuberPromo.coins_per_use)
    await callback.message.edit_text(
        f"🎬 <b>Создание промокода</b>\n\n"
        f"💰 Ваш баланс: {user['balance']} монет\n\n"
        "Сколько монет за одну активацию?",
        reply_markup=kb.get_back_button("my_balance"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(YouTuberPromo.coins_per_use)
async def yt_promo_coins(message: Message, state: FSMContext):
    try:
        coins = int(message.text)
        if coins < 1:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    user = await db.get_user(message.from_user.id)
    max_uses = user['balance'] // coins
    
    if max_uses < 1:
        await message.answer("❌ Недостаточно монет")
        return
    
    await state.update_data(coins=coins, max_possible=max_uses)
    await state.set_state(YouTuberPromo.max_uses)
    await message.answer(f"Сколько активаций? (максимум {max_uses})")

@router.message(YouTuberPromo.max_uses)
async def yt_promo_uses(message: Message, state: FSMContext):
    try:
        uses = int(message.text)
        if uses < 1:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    data = await state.get_data()
    total_cost = data['coins'] * uses
    
    user = await db.get_user(message.from_user.id)
    if user['balance'] < total_cost:
        await message.answer(f"❌ Нужно {total_cost} монет, у вас {user['balance']}")
        return
    
    # Списываем и создаём
    await db.update_balance(message.from_user.id, -total_cost, "Создание промокода")
    code = db.generate_promo_code()
    await db.create_promocode(code, data['coins'], uses, message.from_user.id)
    await state.clear()
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎁 Код: <code>{code}</code>\n"
        f"💰 {data['coins']} монет x {uses} активаций",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== ТОП =====
@router.callback_query(F.data == "top_players")
async def top_players(callback: CallbackQuery):
    top = await db.get_top_users(10)
    
    text = "🏆 <b>Топ-10 игроков</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, u in enumerate(top, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        name = u['full_name'] or u['username'] or 'Аноним'
        text += f"{medal} <b>{name}</b> — {u['total_earned']:,} 💰\n"
    
    if not top:
        text += "<i>Пока пусто</i>"
    
    await callback.message.edit_text(text, reply_markup=kb.get_back_button("main_menu"), parse_mode="HTML")
    await callback.answer()

# ===== ИСТОРИЯ =====
@router.callback_query(F.data == "balance_history")
async def balance_history(callback: CallbackQuery):
    # Упрощённая история
    user = await db.get_user(callback.from_user.id)
    subs = await db.get_user_submissions(callback.from_user.id, 5)
    wds = await db.get_user_withdrawals(callback.from_user.id, 5)
    
    text = "📜 <b>История операций</b>\n\n"
    
    if subs:
        text += "<b>Последние заявки:</b>\n"
        for s in subs:
            st = {"pending": "🟡", "completed": "✅", "rejected": "❌"}.get(s['status'], "❓")
            text += f"• {st} Задание #{s['task_id']}\n"
    
    if wds:
        text += "\n<b>Последние выводы:</b>\n"
        for w in wds:
            st = {"pending": "🟡", "completed": "✅", "rejected": "❌"}.get(w['status'], "❓")
            text += f"• {st} {w['coins']} монет\n"
    
    if not subs and not wds:
        text += "<i>Пока пусто</i>"
    
    await callback.message.edit_text(text, reply_markup=kb.get_back_button("my_balance"), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "my_submissions")
async def my_submissions(callback: CallbackQuery):
    subs = await db.get_user_submissions(callback.from_user.id, 10)
    
    text = "📋 <b>Мои заявки</b>\n\n"
    
    if subs:
        for s in subs:
            st = {"pending": "🟡", "completed": "✅", "rejected": "❌"}.get(s['status'], "❓")
            t = "🎮" if s['task_type'] == 'game' else "💳"
            text += f"• {t} #{s['task_id']} — {st}\n"
            if s.get('admin_comment'):
                text += f"  💬 <i>{s['admin_comment']}</i>\n"
    else:
        text += "<i>Нет заявок</i>"
    
    await callback.message.edit_text(text, reply_markup=kb.get_back_button("tasks_menu"), parse_mode="HTML")
    await callback.answer()
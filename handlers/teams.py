from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import PLAYER_PROFILE_COST, CLAN_PROFILE_COST
from states import PlayerProfile, ClanProfile

router = Router()

# ===== МЕНЮ ТИММЕЙТОВ =====
@router.callback_query(F.data == "teams_menu")
async def teams_menu(callback: CallbackQuery):
    text = f"""
👥 <b>Поиск тиммейтов</b>

👤 <b>Анкета игрока</b> — {PLAYER_PROFILE_COST} монет / неделя
🏰 <b>Анкета клана</b> — {CLAN_PROFILE_COST} монет / 2 недели

Создайте анкету или найдите тиммейта!
"""
    await callback.message.edit_text(text, reply_markup=kb.get_teams_menu(), parse_mode="HTML")
    await callback.answer()

# ===== ПРОСМОТР ИГРОКОВ =====
@router.callback_query(F.data == "view_players")
async def view_players(callback: CallbackQuery):
    profiles = await db.get_active_player_profiles()
    
    if not profiles:
        text = "👤 <b>Анкеты игроков</b>\n\n😔 Пока никого нет"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("teams_menu"), parse_mode="HTML")
    else:
        text = f"👤 <b>Анкеты игроков</b>\n\nНайдено: {len(profiles)}"
        await callback.message.edit_text(
            text, 
            reply_markup=kb.get_profiles_list(profiles, "player"), 
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("view_player_"))
async def view_player_profile(callback: CallbackQuery):
    profile_id = int(callback.data.split("_")[-1])
    profiles = await db.get_active_player_profiles()
    profile = next((p for p in profiles if p['id'] == profile_id), None)
    
    if not profile:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    text = f"""
👤 <b>Анкета игрока</b>

━━━━━━━━━━━━━━━━━━

📛 <b>Имя:</b> {profile['real_name']}
🎮 <b>Ник:</b> {profile['nickname']}
🌐 <b>Сервер:</b> {profile['server']}
📅 <b>Возраст:</b> {profile['age']} лет
⏱ <b>Играет:</b> {profile['hours_played']}

🏰 <b>Был в кланах:</b>
{profile['prev_clans'] or 'Не был'}

━━━━━━━━━━━━━━━━━━

📱 Контакт: @{profile.get('username') or 'скрыт'}
"""
    await callback.message.edit_text(text, reply_markup=kb.get_back_button("view_players"), parse_mode="HTML")
    await callback.answer()

# ===== ПРОСМОТР КЛАНОВ =====
@router.callback_query(F.data == "view_clans")
async def view_clans(callback: CallbackQuery):
    profiles = await db.get_active_clan_profiles()
    
    if not profiles:
        text = "🏰 <b>Анкеты кланов</b>\n\n😔 Пока ничего нет"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("teams_menu"), parse_mode="HTML")
    else:
        text = f"🏰 <b>Анкеты кланов</b>\n\nНайдено: {len(profiles)}"
        await callback.message.edit_text(
            text, 
            reply_markup=kb.get_profiles_list(profiles, "clan"), 
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("view_clan_"))
async def view_clan_profile(callback: CallbackQuery):
    profile_id = int(callback.data.split("_")[-1])
    profiles = await db.get_active_clan_profiles()
    profile = next((p for p in profiles if p['id'] == profile_id), None)
    
    if not profile:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    text = f"""
🏰 <b>Анкета клана</b>

━━━━━━━━━━━━━━━━━━

🏷 <b>Название:</b> {profile['clan_name']}
🔖 <b>Тег:</b> [{profile['clan_tag']}]
🌐 <b>Сервер:</b> {profile['server']}
📅 <b>Основан:</b> {profile['founded_date']}
⏱ <b>Требуется часов/день:</b> {profile['hours_required']}

━━━━━━━━━━━━━━━━━━

📱 Лидер: @{profile.get('username') or 'скрыт'}
"""
    await callback.message.edit_text(text, reply_markup=kb.get_back_button("view_clans"), parse_mode="HTML")
    await callback.answer()

# ===== СОЗДАНИЕ АНКЕТЫ ИГРОКА =====
@router.callback_query(F.data == "create_player_profile")
async def create_player_start(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < PLAYER_PROFILE_COST:
        await callback.answer(f"❌ Нужно {PLAYER_PROFILE_COST} монет!", show_alert=True)
        return
    
    await state.set_state(PlayerProfile.age)
    await callback.message.edit_text(
        f"📝 <b>Создание анкеты</b>\n\n"
        f"💰 Стоимость: {PLAYER_PROFILE_COST} монет\n"
        f"⏱ Срок: 1 неделя\n\n"
        f"Введите ваш <b>возраст</b>:",
        reply_markup=kb.get_back_button("teams_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(PlayerProfile.age)
async def player_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 10 or age > 100:
            raise ValueError
    except:
        await message.answer("⚠️ Введите корректный возраст (10-100)")
        return
    
    await state.update_data(age=age)
    await state.set_state(PlayerProfile.hours)
    await message.answer("⏱ Сколько часов в игре? (например: 500ч или 2000+ч)")

@router.message(PlayerProfile.hours)
async def player_hours(message: Message, state: FSMContext):
    await state.update_data(hours=message.text)
    await state.set_state(PlayerProfile.name)
    await message.answer("📛 Ваше имя:")

@router.message(PlayerProfile.name)
async def player_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(PlayerProfile.nickname)
    await message.answer("🎮 Ваш игровой никнейм:")

@router.message(PlayerProfile.nickname)
async def player_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(PlayerProfile.server)
    await message.answer("🌐 На каком сервере играете?")

@router.message(PlayerProfile.server)
async def player_server(message: Message, state: FSMContext):
    await state.update_data(server=message.text)
    await state.set_state(PlayerProfile.prev_clans)
    await message.answer(
        "🏰 Были в кланах? Если да — напишите названия и теги.\n"
        "Если нет — напишите 'нет'"
    )

@router.message(PlayerProfile.prev_clans)
async def player_prev_clans(message: Message, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    
    if user['balance'] < PLAYER_PROFILE_COST:
        await state.clear()
        await message.answer("❌ Недостаточно монет!")
        return
    
    prev_clans = message.text if message.text.lower() != 'нет' else None
    
    await db.update_balance(message.from_user.id, -PLAYER_PROFILE_COST, "Анкета игрока")
    await db.create_player_profile(
        message.from_user.id,
        data['age'],
        data['hours'],
        data['name'],
        data['nickname'],
        data['server'],
        prev_clans
    )
    await state.clear()
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        "✅ <b>Анкета создана!</b>\n\n"
        "Она будет активна 7 дней.",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== СОЗДАНИЕ АНКЕТЫ КЛАНА =====
@router.callback_query(F.data == "create_clan_profile")
async def create_clan_start(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < CLAN_PROFILE_COST:
        await callback.answer(f"❌ Нужно {CLAN_PROFILE_COST} монет!", show_alert=True)
        return
    
    await state.set_state(ClanProfile.name)
    await callback.message.edit_text(
        f"🏰 <b>Создание анкеты клана</b>\n\n"
        f"💰 Стоимость: {CLAN_PROFILE_COST} монет\n"
        f"⏱ Срок: 2 недели\n\n"
        f"Введите <b>название клана</b>:",
        reply_markup=kb.get_back_button("teams_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ClanProfile.name)
async def clan_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ClanProfile.tag)
    await message.answer("🔖 Тег клана (например: ABC):")

@router.message(ClanProfile.tag)
async def clan_tag(message: Message, state: FSMContext):
    await state.update_data(tag=message.text.upper())
    await state.set_state(ClanProfile.avatar)
    await message.answer(
        "🖼 Отправьте аватарку клана (фото) или напишите 'пропустить':"
    )

@router.message(ClanProfile.avatar, F.photo)
async def clan_avatar_photo(message: Message, state: FSMContext):
    await state.update_data(avatar=message.photo[-1].file_id)
    await state.set_state(ClanProfile.founded)
    await message.answer("📅 Дата основания клана (например: Январь 2023):")

@router.message(ClanProfile.avatar)
async def clan_avatar_skip(message: Message, state: FSMContext):
    if message.text.lower() in ['пропустить', 'skip', '-']:
        await state.update_data(avatar=None)
        await state.set_state(ClanProfile.founded)
        await message.answer("📅 Дата основания клана:")
    else:
        await message.answer("⚠️ Отправьте фото или напишите 'пропустить'")

@router.message(ClanProfile.founded)
async def clan_founded(message: Message, state: FSMContext):
    await state.update_data(founded=message.text)
    await state.set_state(ClanProfile.server)
    await message.answer("🌐 Основной сервер клана:")

@router.message(ClanProfile.server)
async def clan_server(message: Message, state: FSMContext):
    await state.update_data(server=message.text)
    await state.set_state(ClanProfile.hours_required)
    await message.answer("⏱ Сколько часов в день требуется от игрока?")

@router.message(ClanProfile.hours_required)
async def clan_hours(message: Message, state: FSMContext):
    try:
        hours = int(message.text.replace("ч", "").replace("h", "").strip())
    except:
        hours = 0
    
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    
    if user['balance'] < CLAN_PROFILE_COST:
        await state.clear()
        await message.answer("❌ Недостаточно монет!")
        return
    
    await db.update_balance(message.from_user.id, -CLAN_PROFILE_COST, "Анкета клана")
    await db.create_clan_profile(
        message.from_user.id,
        data['name'],
        data['tag'],
        data.get('avatar'),
        data['founded'],
        data['server'],
        hours
    )
    await state.clear()
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        "✅ <b>Анкета клана создана!</b>\n\n"
        "Она будет активна 14 дней.",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )
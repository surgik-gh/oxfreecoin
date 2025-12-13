from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import random
import asyncio

import database as db
import keyboards as kb
from config import MIN_BET, WIN_CHANCE, ROULETTE_MULTIPLIERS
from states import PlayGame

router = Router()

# ===== МЕНЮ ИГР =====
@router.callback_query(F.data == "games_menu")
async def games_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    
    text = f"""
🎮 <b>Мини-игры</b>

💰 Монеты: <b>{user['balance']:,}</b>
🪙 Серебро: <b>{user['demo_balance']:,}</b>

🎯 Мин. ставка: <b>{MIN_BET}</b>

Выберите игру:
"""
    await callback.message.edit_text(text, reply_markup=kb.get_games_menu(), parse_mode="HTML")
    await callback.answer()

# ===== ВЫБОР ТИПА СТАВКИ =====
async def start_game(callback: CallbackQuery, state: FSMContext, game: str):
    await state.set_state(PlayGame.bet_type)
    await state.update_data(game=game)
    
    await callback.message.edit_text(
        f"🎮 <b>{game.upper()}</b>\n\nВыберите тип ставки:",
        reply_markup=kb.get_bet_type_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "game_cube")
async def game_cube(callback: CallbackQuery, state: FSMContext):
    await start_game(callback, state, "cube")

@router.callback_query(F.data == "game_basketball")
async def game_basketball(callback: CallbackQuery, state: FSMContext):
    await start_game(callback, state, "basketball")

@router.callback_query(F.data == "game_darts")
async def game_darts(callback: CallbackQuery, state: FSMContext):
    await start_game(callback, state, "darts")

@router.callback_query(F.data == "game_roulette")
async def game_roulette(callback: CallbackQuery, state: FSMContext):
    await start_game(callback, state, "roulette")

@router.callback_query(F.data == "game_minesweeper")
async def game_minesweeper(callback: CallbackQuery, state: FSMContext):
    await start_game(callback, state, "minesweeper")

@router.callback_query(PlayGame.bet_type, F.data.in_(["bet_real", "bet_demo"]))
async def select_bet_type(callback: CallbackQuery, state: FSMContext):
    is_demo = callback.data == "bet_demo"
    await state.update_data(is_demo=is_demo)
    await state.set_state(PlayGame.bet)
    
    user = await db.get_user(callback.from_user.id)
    balance = user['demo_balance'] if is_demo else user['balance']
    currency = "серебра" if is_demo else "монет"
    
    await callback.message.edit_text(
        f"💵 Баланс: <b>{balance:,}</b> {currency}\n\n"
        f"Введите ставку (мин. {MIN_BET}):",
        reply_markup=kb.get_back_button("games_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(PlayGame.bet)
async def process_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text.replace(" ", "").replace(",", ""))
        if bet < MIN_BET:
            raise ValueError
    except:
        await message.answer(f"⚠️ Мин. ставка: {MIN_BET}")
        return
    
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    balance = user['demo_balance'] if data['is_demo'] else user['balance']
    
    if balance < bet:
        await message.answer("❌ Недостаточно средств!")
        return
    
    await state.update_data(bet=bet)
    game = data['game']
    
    if game == "cube":
        await state.set_state(PlayGame.cube_guess)
        await message.answer(
            f"🎲 Ставка: <b>{bet}</b>\n\nУгадайте число (1-6):",
            reply_markup=kb.get_cube_choices(),
            parse_mode="HTML"
        )
    
    elif game == "roulette":
        await state.set_state(PlayGame.roulette)
        await message.answer(
            f"🎰 Ставка: <b>{bet}</b>\n\nВыберите множитель:",
            reply_markup=kb.get_roulette_multipliers(),
            parse_mode="HTML"
        )
    
    elif game == "minesweeper":
        await db.update_balance(message.from_user.id, -bet, "Ставка: сапёр", data['is_demo'])
        bombs = random.sample(range(9), 3)
        
        await state.set_state(PlayGame.minesweeper)
        await state.update_data(bombs=bombs, revealed=[], multiplier=1.0)
        
        await message.answer(
            f"💣 <b>Сапёр</b>\n\n"
            f"💰 Ставка: {bet}\n"
            f"🎯 Множитель: x1.0\n"
            f"💵 Выигрыш: {bet}",
            reply_markup=kb.get_minesweeper_board(bombs, []),
            parse_mode="HTML"
        )
    
    elif game in ["basketball", "darts"]:
        await state.clear()
        await db.update_balance(message.from_user.id, -bet, f"Ставка: {game}", data['is_demo'])
        
        emoji = "🏀" if game == "basketball" else "🎯"
        await message.answer(f"{emoji} Бросаем...")
        dice = await message.answer_dice(emoji=emoji)
        await asyncio.sleep(4)
        
        # 8% шанс или успешный бросок
        if game == "basketball":
            win = random.random() < WIN_CHANCE or dice.dice.value >= 4
        else:
            win = random.random() < WIN_CHANCE or dice.dice.value == 6
        
        if win:
            winnings = bet * 2
            await db.update_balance(message.from_user.id, winnings, f"Выигрыш: {game}", data['is_demo'])
            result = f"🎉 <b>Победа!</b>\n💰 +{winnings}"
        else:
            result = f"😔 <b>Мимо!</b>\n💸 -{bet}"
        
        await message.answer(result, reply_markup=kb.get_games_menu(), parse_mode="HTML")

# ===== КУБИК =====
@router.callback_query(PlayGame.cube_guess, F.data.startswith("cube_guess_"))
async def cube_guess(callback: CallbackQuery, state: FSMContext):
    guess = int(callback.data.split("_")[-1])
    data = await state.get_data()
    bet = data['bet']
    is_demo = data['is_demo']
    
    await state.clear()
    await db.update_balance(callback.from_user.id, -bet, "Ставка: кубик", is_demo)
    
    await callback.message.edit_text(f"🎲 Выбор: <b>{guess}</b>\n\nБросаем...", parse_mode="HTML")
    dice = await callback.message.answer_dice(emoji="🎲")
    await asyncio.sleep(4)
    
    actual = dice.dice.value
    win = random.random() < WIN_CHANCE or actual == guess
    
    if win:
        winnings = bet * 2
        await db.update_balance(callback.from_user.id, winnings, "Выигрыш: кубик", is_demo)
        result = f"🎉 <b>Угадали!</b>\n🎲 Выпало: {actual if actual == guess else guess}\n💰 +{winnings}"
    else:
        result = f"😔 <b>Не угадали!</b>\n🎲 Выпало: {actual}\n💸 -{bet}"
    
    await callback.message.answer(result, reply_markup=kb.get_games_menu(), parse_mode="HTML")
    await callback.answer()

# ===== РУЛЕТКА =====
@router.callback_query(PlayGame.roulette, F.data.startswith("roulette_"))
async def roulette_spin(callback: CallbackQuery, state: FSMContext):
    target_mult = float(callback.data.split("_")[1])
    data = await state.get_data()
    bet = data['bet']
    is_demo = data['is_demo']
    
    await state.clear()
    await db.update_balance(callback.from_user.id, -bet, "Ставка: рулетка", is_demo)
    
    # Выбираем результат по шансам
    roll = random.random()
    cumulative = 0
    result_mult = 1.5
    
    for mult, chance in ROULETTE_MULTIPLIERS.items():
        cumulative += chance
        if roll <= cumulative:
            result_mult = mult
            break
    
    # 8% шанс получить выбранный множитель
    if random.random() < WIN_CHANCE:
        result_mult = target_mult
    
    await callback.message.edit_text("🎰 Крутим рулетку...", parse_mode="HTML")
    await asyncio.sleep(2)
    
    if result_mult == target_mult:
        winnings = int(bet * result_mult)
        await db.update_balance(callback.from_user.id, winnings, "Выигрыш: рулетка", is_demo)
        result = f"🎉 <b>Выпало x{result_mult}!</b>\n💰 +{winnings}"
    else:
        result = f"😔 <b>Выпало x{result_mult}</b>\nВы ставили на x{target_mult}\n💸 -{bet}"
    
    await callback.message.edit_text(result, reply_markup=kb.get_games_menu(), parse_mode="HTML")
    await callback.answer()

# ===== САПЁР =====
@router.callback_query(PlayGame.minesweeper, F.data.startswith("mine_"))
async def minesweeper_click(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("mine_", "")
    
    if action == "none":
        await callback.answer()
        return
    
    data = await state.get_data()
    bombs = data['bombs']
    revealed = data['revealed']
    bet = data['bet']
    multiplier = data['multiplier']
    is_demo = data['is_demo']
    
    if action == "cashout":
        winnings = int(bet * multiplier)
        await db.update_balance(callback.from_user.id, winnings, "Выигрыш: сапёр", is_demo)
        await state.clear()
        
        await callback.message.edit_text(
            f"💰 <b>Забрали выигрыш!</b>\n\nx{multiplier} = +{winnings}",
            reply_markup=kb.get_games_menu(),
            parse_mode="HTML"
        )
        await callback.answer("💰 Получено!")
        return
    
    cell = int(action)
    if cell in revealed:
        await callback.answer()
        return
    
    if cell in bombs:
        # 8% шанс спасения
        if random.random() < WIN_CHANCE:
            available = [i for i in range(9) if i not in bombs and i not in revealed and i != cell]
            if available:
                bombs.remove(cell)
                bombs.append(random.choice(available))
        
        if cell in bombs:
            revealed.append(cell)
            await state.clear()
            
            await callback.message.edit_text(
                f"💥 <b>БОМБА!</b>\n\n💸 -{bet}",
                reply_markup=kb.get_minesweeper_board(bombs, revealed, True),
                parse_mode="HTML"
            )
            await callback.answer("💥 Бомба!")
            return
    
    revealed.append(cell)
    multiplier += 0.5
    
    # Полная победа
    safe_cells = [i for i in range(9) if i not in bombs]
    if all(c in revealed for c in safe_cells):
        multiplier = 5.0
        winnings = int(bet * multiplier)
        await db.update_balance(callback.from_user.id, winnings, "Выигрыш: сапёр (полный)", is_demo)
        await state.clear()
        
        await callback.message.edit_text(
            f"🎉 <b>ВСЕ ОТКРЫТО!</b>\n\nx{multiplier} = +{winnings}",
            reply_markup=kb.get_minesweeper_board(bombs, revealed, True),
            parse_mode="HTML"
        )
        await callback.answer("🎉 Победа!")
        return
    
    await state.update_data(bombs=bombs, revealed=revealed, multiplier=multiplier)
    
    current = int(bet * multiplier)
    await callback.message.edit_text(
        f"💣 <b>Сапёр</b>\n\n"
        f"💰 Ставка: {bet}\n"
        f"🎯 Множитель: x{multiplier}\n"
        f"💵 Выигрыш: {current}",
        reply_markup=kb.get_minesweeper_board(bombs, revealed),
        parse_mode="HTML"
    )
    await callback.answer("✅ Безопасно!")
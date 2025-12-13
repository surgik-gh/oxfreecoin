from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import PRIVILEGES
from states import CreateMarketItem

router = Router()
# ===== МЕНЮ РЫНКА =====
@router.callback_query(F.data == "market_menu")
async def market_menu(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    
    if not user:
        await db.create_user(
            callback.from_user.id,
            callback.from_user.username or "",
            callback.from_user.full_name or ""
        )
        user = await db.get_user(callback.from_user.id)
    
    balance = user['balance'] if user else 0
    
    text = f"""
🛒 <b>Рынок</b>

💰 Баланс: <b>{balance:,}</b> монет

Здесь можно купить бонусы, привилегии и другие товары.
"""
    await callback.message.edit_text(text, reply_markup=kb.get_market_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "market_items")
async def market_items(callback: CallbackQuery):
    items = await db.get_market_items()
    
    if not items:
        text = "🛍 <b>Товары</b>\n\n😔 Пока ничего нет"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("market_menu"), parse_mode="HTML")
    else:
        text = f"🛍 <b>Товары</b>\n\nДоступно: {len(items)}"
        await callback.message.edit_text(text, reply_markup=kb.get_market_items_list(items), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("market_item_"))
async def view_market_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    item = await db.get_market_item(item_id)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    user = await db.get_user(callback.from_user.id)
    already_bought = await db.has_purchased_item(callback.from_user.id, item_id)
    can_buy = user['balance'] >= item['price'] and not already_bought
    
    # Описание награды
    if item['reward_type'] == 'coins':
        reward_text = f"💰 {item['reward_value']} монет"
    elif item['reward_type'] == 'privilege':
        priv = PRIVILEGES.get(item['reward_value'], {})
        reward_text = f"🎖 Привилегия: {priv.get('name', item['reward_value'])}"
    elif item['reward_type'] == 'promo_ability':
        reward_text = f"🎁 Возможность создать {item['reward_value']} промокод(ов)"
    else:
        reward_text = item['reward_value']
    
    text = f"""
🏷 <b>{item['name']}</b>

💰 Цена: <b>{item['price']}</b> монет

📝 {item['description']}

🎁 <b>Вы получите:</b>
{reward_text}
"""
    
    if already_bought:
        text += "\n✅ <i>Вы уже купили это</i>"
    elif user['balance'] < item['price']:
        text += "\n❌ <i>Недостаточно монет</i>"
    
    await callback.message.edit_text(
        text, 
        reply_markup=kb.get_market_item_buttons(item_id, can_buy), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_market_"))
async def buy_market_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    item = await db.get_market_item(item_id)
    
    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    user = await db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    if user['balance'] < item['price']:
        await callback.answer("❌ Недостаточно монет!", show_alert=True)
        return
    
    if await db.has_purchased_item(callback.from_user.id, item_id):
        await callback.answer("❌ Вы уже купили это!", show_alert=True)
        return
    
    # Списываем деньги
    await db.update_balance(callback.from_user.id, -item['price'], f"Покупка: {item['name']}")
    await db.purchase_market_item(callback.from_user.id, item_id)
    
    # Выдаём награду
    reward_text = ""
    if item['reward_type'] == 'coins':
        coins = int(item['reward_value'])
        await db.update_balance(callback.from_user.id, coins, f"Награда: {item['name']}")
        reward_text = f"💰 +{coins} монет"
    
    elif item['reward_type'] == 'privilege':
        await db.set_user_privilege(callback.from_user.id, item['reward_value'])
        priv = PRIVILEGES.get(item['reward_value'], {})
        reward_text = f"🎖 Привилегия: {priv.get('name', item['reward_value'])}"
    
    elif item['reward_type'] == 'promo_ability':
        count = int(item['reward_value'])
        await db.add_promo_ability(callback.from_user.id, count)
        reward_text = f"🎁 +{count} возможность создать промокод"
    
    is_admin = await db.is_admin(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"🏷 {item['name']}\n"
        f"{reward_text}",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )
    await callback.answer("✅ Куплено!")

@router.callback_query(F.data == "my_purchases")
async def my_purchases(callback: CallbackQuery):
    # Упрощённо показываем
    await callback.message.edit_text(
        "📦 <b>Мои покупки</b>\n\n<i>История покупок сохраняется.</i>",
        reply_markup=kb.get_back_button("market_menu"),
        parse_mode="HTML"
    )
    await callback.answer()
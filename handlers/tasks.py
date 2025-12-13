from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import (
    RESOURCES_CATEGORIES, TASKS_PER_PAGE, 
    TASK_COMMISSION, SUBSCRIPTION_REWARD
)
from states import SubmitTask, CreateUserOrder

router = Router()

# ===== МЕНЮ ЗАДАНИЙ =====
@router.callback_query(F.data == "tasks_menu")
async def tasks_menu(callback: CallbackQuery):
    text = """
📋 <b>Задания</b>

📦 <b>Заказы</b> — создайте или выполните заказ
💳 <b>Карты</b> — оформляйте карты
📢 <b>Подписки</b> — подписывайтесь на каналы
"""
    await callback.message.edit_text(text, reply_markup=kb.get_tasks_menu(), parse_mode="HTML")
    await callback.answer()

# ===== ОТКРЫТЫЕ ЗАКАЗЫ =====
@router.callback_query(F.data.startswith("open_orders_"))
async def open_orders(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    orders, total = await db.get_open_orders(page, TASKS_PER_PAGE)
    
    if not orders and page == 0:
        text = "📦 <b>Открытые заказы</b>\n\n😔 Нет доступных заказов"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("tasks_menu"), parse_mode="HTML")
    else:
        text = f"📦 <b>Открытые заказы</b>\n\nВсего: <b>{total}</b>\n\n<i>Комиссия: {int(TASK_COMMISSION*100)}%</i>"
        await callback.message.edit_text(text, reply_markup=kb.get_orders_list(orders, page, total), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("view_order_"))
async def view_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    category = RESOURCES_CATEGORIES.get(order['resource_category'], {})
    resource_name = category.get('items', {}).get(order['resource_type'], order['resource_type'])
    
    status_text = {
        'open': '🟢 Открыт',
        'in_progress': '🟡 Выполняется',
        'pending_confirm': '🔵 Ожидает подтверждения',
        'completed': '✅ Выполнен',
        'cancelled': '❌ Отменён'
    }.get(order['status'], order['status'])
    
    text = f"""
📦 <b>Заказ #{order['id']}</b>

📊 Статус: {status_text}

━━━━━━━━━━━━━━━━━━

📦 <b>Требуется:</b>
{category.get('emoji', '📦')} {resource_name} — <b>{order['resource_amount']:,}</b> шт.

👤 <b>Заказчик:</b> @{order.get('creator_username') or 'скрыт'}
💰 <b>Награда:</b> {order['executor_reward']} монет <i>(после комиссии {int(TASK_COMMISSION*100)}%)</i>
"""
    
    if order.get('executor_username'):
        text += f"\n🔧 <b>Исполнитель:</b> @{order['executor_username']}"
    
    if order.get('description'):
        text += f"\n\n📝 {order['description']}"
    
    is_creator = order['creator_id'] == callback.from_user.id
    is_executor = order.get('executor_id') == callback.from_user.id
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_order_actions(order_id, is_creator, is_executor, order['status']),
        parse_mode="HTML"
    )
    await callback.answer()

# ===== СОЗДАНИЕ ЗАКАЗА =====
@router.callback_query(F.data == "create_order")
async def create_order_start(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < 10:
        await callback.answer("❌ Минимум 10 монет для создания заказа", show_alert=True)
        return
    
    await state.set_state(CreateUserOrder.category)
    await callback.message.edit_text(
        f"➕ <b>Создание заказа</b>\n\n"
        f"💰 Ваш баланс: {user['balance']} монет\n\n"
        f"Выберите категорию:",
        reply_markup=kb.get_resource_categories(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(CreateUserOrder.category, F.data.startswith("category_"))
async def order_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("category_", "")
    await state.update_data(category=category)
    await state.set_state(CreateUserOrder.resource)
    
    await callback.message.edit_text(
        "Выберите ресурс:",
        reply_markup=kb.get_resource_items(category)
    )
    await callback.answer()

@router.callback_query(CreateUserOrder.resource, F.data.startswith("resource_"))
async def order_resource(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    resource = parts[-1]
    await state.update_data(resource=resource)
    await state.set_state(CreateUserOrder.amount)
    
    await callback.message.edit_text(
        "Введите количество:",
        reply_markup=kb.get_cancel_button()
    )
    await callback.answer()

@router.message(CreateUserOrder.amount)
async def order_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("⚠️ Введите число > 0")
        return
    
    await state.update_data(amount=amount)
    await state.set_state(CreateUserOrder.description)
    
    user = await db.get_user(message.from_user.id)
    
    await message.answer(
        f"💰 Ваш баланс: {user['balance']} монет\n\n"
        f"Введите сумму награды для исполнителя:\n"
        f"<i>(Комиссия {int(TASK_COMMISSION*100)}% уже учтена)</i>",
        parse_mode="HTML"
    )

@router.message(CreateUserOrder.description)
async def order_description(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Первый ввод - это награда
    if 'reward' not in data:
        try:
            executor_reward = int(message.text.replace(" ", "").replace(",", ""))
            if executor_reward < 5:
                await message.answer("⚠️ Минимальная награда: 5 монет")
                return
        except:
            await message.answer("⚠️ Введите число")
            return
        
        # Считаем полную стоимость
        total_reward = int(executor_reward / (1 - TASK_COMMISSION))
        
        user = await db.get_user(message.from_user.id)
        if user['balance'] < total_reward:
            await message.answer(
                f"❌ Недостаточно монет!\n"
                f"Нужно: {total_reward} (включая комиссию)\n"
                f"У вас: {user['balance']}"
            )
            return
        
        await state.update_data(reward=executor_reward, total=total_reward)
        await message.answer("Введите описание заказа (или '-' чтобы пропустить):")
        return
    
    # Второй ввод - описание
    description = message.text if message.text != "-" else ""
    
    user = await db.get_user(message.from_user.id)
    total = data['total']
    
    if user['balance'] < total:
        await state.clear()
        await message.answer("❌ Недостаточно монет!")
        return
    
    # Списываем деньги и создаём заказ
    await db.update_balance(message.from_user.id, -total, f"Создание заказа")
    
    order_id = await db.create_game_order(
        message.from_user.id,
        data['category'],
        data['resource'],
        data['amount'],
        total,
        data['reward'],
        description
    )
    
    await state.clear()
    
    category = RESOURCES_CATEGORIES.get(data['category'], {})
    resource_name = category.get('items', {}).get(data['resource'], data['resource'])
    
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
        f"📦 {resource_name} — {data['amount']} шт.\n"
        f"💰 Награда исполнителю: {data['reward']} монет\n"
        f"💸 Списано с баланса: {total} монет",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML"
    )

# ===== ВЗЯТЬ ЗАКАЗ =====
@router.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    
    success = await db.take_order(order_id, callback.from_user.id)
    
    if not success:
        await callback.answer("❌ Не удалось взять заказ", show_alert=True)
        return
    
    await callback.answer("✅ Вы взяли заказ!", show_alert=True)
    
    # Показываем обновлённый заказ
    order = await db.get_order(order_id)
    category = RESOURCES_CATEGORIES.get(order['resource_category'], {})
    resource_name = category.get('items', {}).get(order['resource_type'], order['resource_type'])
    
    text = f"""
✅ <b>Вы взяли заказ #{order_id}!</b>

📦 Нужно собрать: {category.get('emoji', '📦')} {resource_name} — <b>{order['resource_amount']:,}</b> шт.

👤 Отдать заказчику: @{order.get('creator_username') or 'скрыт'}

💰 Награда: {order['executor_reward']} монет

После выполнения отправьте скриншот.
"""
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_order_actions(order_id, False, True, 'in_progress'),
        parse_mode="HTML"
    )

# ===== ОТПРАВИТЬ ДОКАЗАТЕЛЬСТВО =====
@router.callback_query(F.data.startswith("submit_order_"))
async def submit_order_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[-1])
    
    await state.set_state(SubmitTask.proof)
    await state.update_data(order_id=order_id, task_type="order")
    
    await callback.message.edit_text(
        "📸 <b>Отправьте скриншот</b>\n\n"
        "Скриншот должен подтверждать передачу ресурсов.",
        reply_markup=kb.get_back_button("tasks_menu"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SubmitTask.proof, F.photo)
async def submit_order_proof(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    
    if data.get('task_type') == 'order':
        order_id = data['order_id']
        order = await db.get_order(order_id)
        
        if not order:
            await state.clear()
            await message.answer("❌ Заказ не найден")
            return
        
        # Меняем статус на ожидание подтверждения
        async with db.aiosqlite.connect(db.DATABASE_PATH) as conn:
            await conn.execute(
                "UPDATE game_orders SET status = 'pending_confirm' WHERE id = ?",
                (order_id,)
            )
            await conn.commit()
        
        # Отправляем фото заказчику
        try:
            await bot.send_photo(
                order['creator_id'],
                message.photo[-1].file_id,
                caption=f"📸 <b>Доказательство по заказу #{order_id}</b>\n\n"
                        f"Исполнитель: @{message.from_user.username or 'скрыт'}\n\n"
                        f"Подтвердите выполнение в боте.",
                parse_mode="HTML"
            )
        except:
            pass
        
        await state.clear()
        
        is_admin = await db.is_admin(message.from_user.id)
        await message.answer(
            f"✅ <b>Доказательство отправлено!</b>\n\n"
            f"Ожидайте подтверждения от заказчика.",
            reply_markup=kb.get_main_menu(is_admin),
            parse_mode="HTML"
        )
    else:
        # Обычная логика для заданий с картами
        photo_id = message.photo[-1].file_id
        sub_id = await db.submit_task(
            message.from_user.id,
            data['task_id'],
            data['task_type'],
            photo_id
        )
        await state.clear()
        
        is_admin = await db.is_admin(message.from_user.id)
        await message.answer(
            f"✅ <b>Заявка #{sub_id} отправлена!</b>",
            reply_markup=kb.get_main_menu(is_admin),
            parse_mode="HTML"
        )

@router.message(SubmitTask.proof)
async def submit_wrong(message: Message):
    await message.answer("⚠️ Отправьте <b>фото</b>", parse_mode="HTML")

# ===== ПОДТВЕРЖДЕНИЕ ЗАКАЗА =====
@router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[-1])
    order = await db.get_order(order_id)
    
    if not order or order['creator_id'] != callback.from_user.id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Завершаем заказ
    await db.complete_order(order_id)
    
    # Выплачиваем исполнителю
    await db.update_balance(
        order['executor_id'],
        order['executor_reward'],
        f"Выполнение заказа #{order_id}"
    )
    
    # Уведомляем исполнителя
    try:
        await bot.send_message(
            order['executor_id'],
            f"✅ <b>Заказ #{order_id} подтверждён!</b>\n\n"
            f"💰 +{order['executor_reward']} монет",
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"✅ <b>Заказ #{order_id} выполнен!</b>\n\n"
        f"Исполнителю выплачено {order['executor_reward']} монет.",
        reply_markup=kb.get_back_button("tasks_menu"),
        parse_mode="HTML"
    )
    await callback.answer("✅ Подтверждено!")

@router.callback_query(F.data.startswith("reject_order_"))
async def reject_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[-1])
    order = await db.get_order(order_id)
    
    if not order or order['creator_id'] != callback.from_user.id:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Возвращаем в статус выполнения
    async with db.aiosqlite.connect(db.DATABASE_PATH) as conn:
        await conn.execute(
            "UPDATE game_orders SET status = 'in_progress' WHERE id = ?",
            (order_id,)
        )
        await conn.commit()
    
    # Уведомляем исполнителя
    try:
        await bot.send_message(
            order['executor_id'],
            f"❌ <b>Доказательство по заказу #{order_id} отклонено</b>\n\n"
            f"Попробуйте ещё раз.",
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.message.edit_text(
        f"❌ Доказательство отклонено. Заказ вернулся в работу.",
        reply_markup=kb.get_back_button("tasks_menu")
    )
    await callback.answer("❌ Отклонено")

# ===== ОТМЕНА ЗАКАЗА =====
@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    
    success = await db.cancel_order(order_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅ Заказ отменён, монеты возвращены", show_alert=True)
        await callback.message.edit_text(
            "🚫 <b>Заказ отменён</b>\n\nМонеты возвращены на баланс.",
            reply_markup=kb.get_back_button("tasks_menu"),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Не удалось отменить", show_alert=True)

# ===== МОИ ЗАКАЗЫ =====
@router.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    orders = await db.get_user_orders(callback.from_user.id)
    
    if not orders:
        text = "📋 <b>Мои заказы</b>\n\nУ вас пока нет заказов"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("tasks_menu"), parse_mode="HTML")
    else:
        text = f"📋 <b>Мои заказы</b>\n\n📤 — вы создали\n📥 — вы выполняете"
        await callback.message.edit_text(
            text, 
            reply_markup=kb.get_my_orders_list(orders, callback.from_user.id), 
            parse_mode="HTML"
        )
    await callback.answer()

# ===== ПОДПИСКИ =====
@router.callback_query(F.data == "subscriptions_menu")
async def subscriptions_menu(callback: CallbackQuery):
    text = f"""
📢 <b>Задания с подписками</b>

Подписывайтесь на каналы и получайте монеты!

💰 За каждую подписку: <b>+{SUBSCRIPTION_REWARD}</b> монета
⚠️ За отписку: <b>-{SUBSCRIPTION_REWARD}</b> монета
"""
    await callback.message.edit_text(text, reply_markup=kb.get_subscriptions_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "sub_channels_list")
async def sub_channels_list(callback: CallbackQuery):
    channels = await db.get_subscription_channels()
    
    if not channels:
        await callback.message.edit_text(
            "📢 <b>Каналы для подписки</b>\n\nПока нет доступных каналов",
            reply_markup=kb.get_back_button("subscriptions_menu"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Получаем подписки пользователя
    user_subs = []
    for ch in channels:
        sub = await db.get_user_subscription(callback.from_user.id, ch['channel_id'])
        if sub:
            user_subs.append(ch['channel_id'])
    
    await callback.message.edit_text(
        f"📢 <b>Каналы для подписки</b>\n\n"
        f"✅ — вы подписаны\n"
        f"➕ — подпишитесь",
        reply_markup=kb.get_channels_list(channels, user_subs),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sub_@"))
async def subscribe_channel(callback: CallbackQuery, bot: Bot):
    channel_id = callback.data.replace("sub_", "")
    
    # Проверяем подписку
    try:
        member = await bot.get_chat_member(channel_id, callback.from_user.id)
        if member.status in ['member', 'administrator', 'creator']:
            # Уже подписан, записываем и даём монеты
            existing = await db.get_user_subscription(callback.from_user.id, channel_id)
            if not existing:
                await db.add_user_subscription(callback.from_user.id, channel_id)
                await db.update_balance(callback.from_user.id, SUBSCRIPTION_REWARD, f"Подписка: {channel_id}")
                await callback.answer(f"✅ +{SUBSCRIPTION_REWARD} монета!", show_alert=True)
            else:
                await callback.answer("✅ Вы уже получили награду", show_alert=True)
        else:
            await callback.answer(f"❌ Сначала подпишитесь на {channel_id}", show_alert=True)
    except Exception as e:
        await callback.answer("❌ Ошибка проверки. Подпишитесь и попробуйте снова", show_alert=True)

@router.callback_query(F.data == "check_subscriptions")
async def check_subscriptions(callback: CallbackQuery, bot: Bot):
    channels = await db.get_subscription_channels()
    
    added = 0
    removed = 0
    
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch['channel_id'], callback.from_user.id)
            existing = await db.get_user_subscription(callback.from_user.id, ch['channel_id'])
            
            is_member = member.status in ['member', 'administrator', 'creator']
            
            if is_member and not existing:
                # Новая подписка
                await db.add_user_subscription(callback.from_user.id, ch['channel_id'])
                await db.update_balance(callback.from_user.id, SUBSCRIPTION_REWARD, f"Подписка: {ch['channel_id']}")
                added += 1
            elif not is_member and existing:
                # Отписался
                await db.remove_user_subscription(callback.from_user.id, ch['channel_id'])
                await db.update_balance(callback.from_user.id, -SUBSCRIPTION_REWARD, f"Отписка: {ch['channel_id']}")
                removed += 1
        except:
            continue
    
    text = "🔄 <b>Проверка завершена!</b>\n\n"
    if added:
        text += f"✅ Новых подписок: {added} (+{added * SUBSCRIPTION_REWARD} монет)\n"
    if removed:
        text += f"❌ Отписок: {removed} (-{removed * SUBSCRIPTION_REWARD} монет)\n"
    if not added and not removed:
        text += "Изменений нет"
    
    await callback.answer(text.replace("<b>", "").replace("</b>", ""), show_alert=True)

# ===== ЗАДАНИЯ С КАРТАМИ (оставляем как было) =====
@router.callback_query(F.data.startswith("card_tasks_"))
async def card_tasks(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    tasks, total = await db.get_active_card_tasks(page, TASKS_PER_PAGE)
    
    if not tasks and page == 0:
        text = "💳 <b>Задания с картами</b>\n\n😔 Нет активных заданий"
        await callback.message.edit_text(text, reply_markup=kb.get_back_button("tasks_menu"), parse_mode="HTML")
    else:
        text = f"💳 <b>Задания с картами</b>\n\nВсего: <b>{total}</b>"
        await callback.message.edit_text(text, reply_markup=kb.get_card_tasks_list(tasks, page, total), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("view_card_task_"))
async def view_card_task(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    task = await db.get_card_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    already = await db.has_user_submitted_task(callback.from_user.id, task_id, 'card')
    
    text = f"""
💳 <b>Задание #{task['id']}</b>

🏦 <b>Карта:</b> {task['card_name']}

📝 <b>Описание:</b>
{task['description']}

🔗 <b>Ссылка:</b>
{task['referral_link']}

💰 <b>Награда:</b> {task['reward']:,} монет
"""
    
    if already:
        text += "\n\n⚠️ <i>Вы уже подали заявку</i>"
        markup = kb.get_back_button("card_tasks_0")
    else:
        markup = kb.get_task_action_buttons(task_id, "card")
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("submit_card_"))
async def submit_card_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[-1])
    
    already = await db.has_user_submitted_task(callback.from_user.id, task_id, 'card')
    if already:
        await callback.answer("❌ Вы уже подавали заявку!", show_alert=True)
        return
    
    await state.set_state(SubmitTask.proof)
    await state.update_data(task_type="card", task_id=task_id)
    
    await callback.message.edit_text(
        "📸 <b>Отправьте скриншот</b>",
        reply_markup=kb.get_back_button("card_tasks_0"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "none")
async def ignore_none(callback: CallbackQuery):
    await callback.answer()
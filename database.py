import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import MAIN_ADMIN_ID, DEMO_BALANCE, PRIVILEGES
import random
import string

DATABASE_PATH = "oxide_bot.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Пользователи
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                demo_balance INTEGER DEFAULT 1000,
                total_earned INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                privilege TEXT DEFAULT 'newbie',
                game_server TEXT,
                game_nickname TEXT,
                avatar_file_id TEXT,
                description TEXT,
                is_registered BOOLEAN DEFAULT FALSE,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily_bonus TIMESTAMP,
                promo_ability INTEGER DEFAULT 0
            )
        ''')
        
        # Администраторы
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                clan_name TEXT,
                game_nick TEXT,
                server_name TEXT,
                is_main_admin BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Игровые задания (от админов)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS game_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                server_name TEXT,
                clan_name TEXT,
                game_nick TEXT,
                resource_category TEXT,
                resource_type TEXT,
                resource_amount INTEGER,
                reward INTEGER,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Задания с картами
        await db.execute('''
            CREATE TABLE IF NOT EXISTS card_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                card_name TEXT,
                referral_link TEXT,
                description TEXT,
                reward INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Пользовательские задания (покупка)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_type TEXT,
                item_type TEXT,
                item_amount INTEGER,
                price_paid INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Выполненные задания
        await db.execute('''
            CREATE TABLE IF NOT EXISTS completed_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                task_type TEXT,
                proof_file_id TEXT,
                status TEXT DEFAULT 'pending',
                admin_comment TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER
            )
        ''')
        
        # Заявки на вывод
        await db.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                pack_id TEXT,
                coins INTEGER,
                game_id TEXT,
                status TEXT DEFAULT 'pending',
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER
            )
        ''')
        
        # Промокоды
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                coins INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                created_by INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Использованные промокоды
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promo_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Рынок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS market_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER,
                description TEXT,
                reward_type TEXT,
                reward_value TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Покупки на рынке
        await db.execute('''
            CREATE TABLE IF NOT EXISTS market_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Анкеты игроков
        await db.execute('''
            CREATE TABLE IF NOT EXISTS player_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                age INTEGER,
                hours_played TEXT,
                real_name TEXT,
                nickname TEXT,
                server TEXT,
                prev_clans TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Анкеты кланов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS clan_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                clan_name TEXT,
                clan_tag TEXT,
                avatar_file_id TEXT,
                founded_date TEXT,
                server TEXT,
                hours_required INTEGER,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Транзакции
        await db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Главный админ
        await db.execute('''
            INSERT OR IGNORE INTO admins (user_id, is_main_admin)
            VALUES (?, TRUE)
        ''', (MAIN_ADMIN_ID,))
        
                # Игровые заказы (от игроков)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS game_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                executor_id INTEGER,
                resource_category TEXT,
                resource_type TEXT,
                resource_amount INTEGER,
                total_reward INTEGER,
                executor_reward INTEGER,
                description TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                taken_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Подписки пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Каналы для подписки
        await db.execute('''
            CREATE TABLE IF NOT EXISTS subscription_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                channel_name TEXT,
                channel_type TEXT DEFAULT 'channel',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.commit()

# ===== ПОЛЬЗОВАТЕЛИ =====
async def get_user(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_user(user_id: int, username: str, full_name: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, full_name, demo_balance)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, full_name, DEMO_BALANCE))
        await db.commit()

async def complete_registration(user_id: int, server: str, nickname: str, 
                                avatar: str = None, description: str = None) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE users SET 
                game_server = ?, game_nickname = ?, avatar_file_id = ?,
                description = ?, is_registered = TRUE
            WHERE user_id = ?
        ''', (server, nickname, avatar, description, user_id))
        await db.commit()

async def update_balance(user_id: int, amount: int, description: str = "", 
                         is_demo: bool = False) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if is_demo:
            await db.execute(
                'UPDATE users SET demo_balance = demo_balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
        else:
            await db.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            if amount > 0:
                await db.execute(
                    'UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?',
                    (amount, user_id)
                )
        
        await db.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, "demo" if is_demo else "real", description))
        await db.commit()

async def set_user_balance(user_id: int, balance: int, is_demo: bool = False) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        field = "demo_balance" if is_demo else "balance"
        await db.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (balance, user_id))
        await db.commit()

async def set_user_privilege(user_id: int, privilege: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET privilege = ? WHERE user_id = ?', (privilege, user_id))
        await db.commit()

async def update_user_privilege_by_days(user_id: int) -> str:
    """Автоматическое обновление привилегии по дням"""
    user = await get_user(user_id)
    if not user:
        return "newbie"
    
    # Если особая привилегия - не меняем
    current = user['privilege']
    if current in ['youtuber', 'admin']:
        return current
    
    reg_date = datetime.fromisoformat(user['registered_at']) if user['registered_at'] else datetime.now()
    days = (datetime.now() - reg_date).days
    
    new_privilege = "newbie"
    if days >= 30:
        new_privilege = "strong"
    elif days >= 7:
        new_privilege = "trainee"
    
    if new_privilege != current:
        await set_user_privilege(user_id, new_privilege)
    
    return new_privilege

async def increment_completed_tasks(user_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET tasks_completed = tasks_completed + 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

async def get_top_users(limit: int = 10) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM users ORDER BY total_earned DESC LIMIT ?', 
            (limit,)
        )
        return [dict(row) for row in await cursor.fetchall()]

async def reset_leaderboard() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET total_earned = 0')
        await db.commit()

async def search_users(query: str) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM users 
            WHERE username LIKE ? OR full_name LIKE ? OR user_id = ?
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%', int(query) if query.isdigit() else 0))
        return [dict(row) for row in await cursor.fetchall()]

async def add_promo_ability(user_id: int, count: int = 1) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET promo_ability = promo_ability + ? WHERE user_id = ?',
            (count, user_id)
        )
        await db.commit()

async def use_promo_ability(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or user['promo_ability'] <= 0:
        return False
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET promo_ability = promo_ability - 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()
    return True

async def claim_daily_bonus(user_id: int) -> Optional[int]:
    """Начисление ежедневного бонуса, возвращает сумму или None"""
    user = await get_user(user_id)
    if not user:
        return None
    
    last_bonus = user.get('last_daily_bonus')
    if last_bonus:
        last_dt = datetime.fromisoformat(last_bonus)
        if (datetime.now() - last_dt).days < 1:
            return None
    
    bonus = 1  # 1 монета в день
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE users SET balance = balance + ?, last_daily_bonus = ?
            WHERE user_id = ?
        ''', (bonus, datetime.now(), user_id))
        await db.commit()
    
    return bonus

# ===== АДМИНИСТРАТОРЫ =====
async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

async def is_main_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM admins WHERE user_id = ? AND is_main_admin = TRUE", 
            (user_id,)
        )
        return await cursor.fetchone() is not None

async def add_admin(user_id: int, username: str, clan_name: str, 
                    game_nick: str, server_name: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO admins (user_id, username, clan_name, game_nick, server_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, clan_name, game_nick, server_name))
        # Также ставим привилегию админа
        await db.execute('UPDATE users SET privilege = ? WHERE user_id = ?', ('admin', user_id))
        await db.commit()

async def remove_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT is_main_admin FROM admins WHERE user_id = ?", 
            (user_id,)
        )
        row = await cursor.fetchone()
        if row and row[0]:
            return False
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE users SET privilege = 'strong' WHERE user_id = ?", (user_id,))
        await db.commit()
        return True

async def get_admin(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_all_admins() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins")
        return [dict(row) for row in await cursor.fetchall()]

async def update_admin_profile(user_id: int, clan_name: str, 
                               game_nick: str, server_name: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE admins SET clan_name = ?, game_nick = ?, server_name = ?
            WHERE user_id = ?
        ''', (clan_name, game_nick, server_name, user_id))
        await db.commit()

# ===== ИГРОВЫЕ ЗАДАНИЯ =====
async def create_game_task(admin_id: int, server_name: str, clan_name: str,
                           game_nick: str, resource_category: str, 
                           resource_type: str, resource_amount: int,
                           reward: int, description: str = "") -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO game_tasks 
            (admin_id, server_name, clan_name, game_nick, resource_category,
             resource_type, resource_amount, reward, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (admin_id, server_name, clan_name, game_nick, resource_category,
              resource_type, resource_amount, reward, description))
        await db.commit()
        return cursor.lastrowid

async def get_active_game_tasks(page: int = 0, per_page: int = 5) -> tuple:
    """Возвращает (tasks, total_count)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Общее количество
        cursor = await db.execute(
            "SELECT COUNT(*) FROM game_tasks WHERE status = 'active'"
        )
        total = (await cursor.fetchone())[0]
        
        # Задания с пагинацией
        cursor = await db.execute('''
            SELECT gt.*, a.clan_name as admin_clan, a.game_nick as admin_nick
            FROM game_tasks gt
            JOIN admins a ON gt.admin_id = a.user_id
            WHERE gt.status = 'active'
            ORDER BY gt.created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, page * per_page))
        
        tasks = [dict(row) for row in await cursor.fetchall()]
        return tasks, total

async def get_game_task(task_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT gt.*, a.clan_name as admin_clan, a.game_nick as admin_nick
            FROM game_tasks gt
            JOIN admins a ON gt.admin_id = a.user_id
            WHERE gt.id = ?
        ''', (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def complete_game_task(task_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE game_tasks SET status = 'completed' WHERE id = ?", 
            (task_id,)
        )
        await db.commit()

async def delete_game_task(task_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE game_tasks SET status = 'deleted' WHERE id = ?", 
            (task_id,)
        )
        await db.commit()

# ===== ЗАДАНИЯ С КАРТАМИ =====
async def create_card_task(admin_id: int, card_name: str, referral_link: str,
                           description: str, reward: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO card_tasks (admin_id, card_name, referral_link, description, reward)
            VALUES (?, ?, ?, ?, ?)
        ''', (admin_id, card_name, referral_link, description, reward))
        await db.commit()
        return cursor.lastrowid

async def get_active_card_tasks(page: int = 0, per_page: int = 5) -> tuple:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM card_tasks WHERE status = 'active'"
        )
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute('''
            SELECT * FROM card_tasks WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, page * per_page))
        
        tasks = [dict(row) for row in await cursor.fetchall()]
        return tasks, total

async def get_card_task(task_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM card_tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def complete_card_task(task_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE card_tasks SET status = 'completed' WHERE id = ?", 
            (task_id,)
        )
        await db.commit()

# ===== ПОЛЬЗОВАТЕЛЬСКИЕ ЗАДАНИЯ =====
async def create_user_task(user_id: int, task_type: str, item_type: str,
                           item_amount: int, price: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO user_tasks (user_id, task_type, item_type, item_amount, price_paid)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, task_type, item_type, item_amount, price))
        await db.commit()
        return cursor.lastrowid

async def get_user_active_tasks_count(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            SELECT COUNT(*) FROM user_tasks 
            WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))
        return (await cursor.fetchone())[0]

async def get_user_tasks(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM user_tasks WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,))
        return [dict(row) for row in await cursor.fetchall()]

# ===== ВЫПОЛНЕННЫЕ ЗАДАНИЯ =====
async def submit_task(user_id: int, task_id: int, task_type: str, 
                      proof_file_id: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO completed_tasks (user_id, task_id, task_type, proof_file_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, task_id, task_type, proof_file_id))
        await db.commit()
        return cursor.lastrowid

async def get_pending_submissions() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT ct.*, u.username, u.full_name
            FROM completed_tasks ct
            JOIN users u ON ct.user_id = u.user_id
            WHERE ct.status = 'pending'
            ORDER BY ct.submitted_at ASC
        ''')
        return [dict(row) for row in await cursor.fetchall()]

async def get_submission(submission_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT ct.*, u.username, u.full_name
            FROM completed_tasks ct
            JOIN users u ON ct.user_id = u.user_id
            WHERE ct.id = ?
        ''', (submission_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def approve_submission(submission_id: int, admin_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM completed_tasks WHERE id = ?", 
            (submission_id,)
        )
        submission = await cursor.fetchone()
        if not submission:
            return None
        
        submission = dict(submission)
        
        # Получаем награду
        if submission['task_type'] == 'game':
            cursor = await db.execute(
                "SELECT reward FROM game_tasks WHERE id = ?", 
                (submission['task_id'],)
            )
            # Помечаем задание выполненным
            await db.execute(
                "UPDATE game_tasks SET status = 'completed' WHERE id = ?",
                (submission['task_id'],)
            )
        else:
            cursor = await db.execute(
                "SELECT reward FROM card_tasks WHERE id = ?", 
                (submission['task_id'],)
            )
            await db.execute(
                "UPDATE card_tasks SET status = 'completed' WHERE id = ?",
                (submission['task_id'],)
            )
        
        task = await cursor.fetchone()
        reward = task[0] if task else 0
        
        await db.execute('''
            UPDATE completed_tasks 
            SET status = 'completed', reviewed_at = ?, reviewed_by = ?
            WHERE id = ?
        ''', (datetime.now(), admin_id, submission_id))
        await db.commit()
        
        submission['reward'] = reward
        return submission

async def reject_submission(submission_id: int, admin_id: int, 
                            comment: str) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM completed_tasks WHERE id = ?", 
            (submission_id,)
        )
        submission = await cursor.fetchone()
        if not submission:
            return None
        
        await db.execute('''
            UPDATE completed_tasks 
            SET status = 'rejected', reviewed_at = ?, reviewed_by = ?, admin_comment = ?
            WHERE id = ?
        ''', (datetime.now(), admin_id, comment, submission_id))
        await db.commit()
        
        return dict(submission)

async def get_user_submissions(user_id: int, limit: int = 10) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM completed_tasks WHERE user_id = ?
            ORDER BY submitted_at DESC LIMIT ?
        ''', (user_id, limit))
        return [dict(row) for row in await cursor.fetchall()]

async def has_user_submitted_task(user_id: int, task_id: int, 
                                   task_type: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            SELECT 1 FROM completed_tasks 
            WHERE user_id = ? AND task_id = ? AND task_type = ? 
            AND status IN ('pending', 'completed')
        ''', (user_id, task_id, task_type))
        return await cursor.fetchone() is not None

# ===== ЗАЯВКИ НА ВЫВОД =====
async def create_withdraw_request(user_id: int, pack_id: str, 
                                   coins: int, game_id: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO withdraw_requests (user_id, pack_id, coins, game_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, pack_id, coins, game_id))
        await db.commit()
        return cursor.lastrowid

async def get_pending_withdrawals() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT wr.*, u.username, u.full_name
            FROM withdraw_requests wr
            JOIN users u ON wr.user_id = u.user_id
            WHERE wr.status = 'pending'
            ORDER BY wr.created_at ASC
        ''')
        return [dict(row) for row in await cursor.fetchall()]

async def get_withdrawal(withdraw_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT wr.*, u.username, u.full_name
            FROM withdraw_requests wr
            JOIN users u ON wr.user_id = u.user_id
            WHERE wr.id = ?
        ''', (withdraw_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def complete_withdrawal(withdraw_id: int, admin_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM withdraw_requests WHERE id = ?", 
            (withdraw_id,)
        )
        wd = await cursor.fetchone()
        if not wd:
            return None
        
        await db.execute('''
            UPDATE withdraw_requests 
            SET status = 'completed', reviewed_at = ?, reviewed_by = ?
            WHERE id = ?
        ''', (datetime.now(), admin_id, withdraw_id))
        await db.commit()
        return dict(wd)

async def reject_withdrawal(withdraw_id: int, admin_id: int, 
                            reason: str) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM withdraw_requests WHERE id = ?", 
            (withdraw_id,)
        )
        wd = await cursor.fetchone()
        if not wd:
            return None
        
        wd = dict(wd)
        
        # Возвращаем монеты
        await db.execute(
            'UPDATE users SET balance = balance + ? WHERE user_id = ?',
            (wd['coins'], wd['user_id'])
        )
        
        await db.execute('''
            UPDATE withdraw_requests 
            SET status = 'rejected', reviewed_at = ?, reviewed_by = ?, admin_comment = ?
            WHERE id = ?
        ''', (datetime.now(), admin_id, reason, withdraw_id))
        await db.commit()
        return wd

async def get_user_withdrawals(user_id: int, limit: int = 5) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM withdraw_requests WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        return [dict(row) for row in await cursor.fetchall()]

# ===== ПРОМОКОДЫ =====
async def create_promocode(code: str, coins: int, max_uses: int, 
                           created_by: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO promocodes (code, coins, max_uses, created_by)
            VALUES (?, ?, ?, ?)
        ''', (code.upper(), coins, max_uses, created_by))
        await db.commit()
        return cursor.lastrowid

async def get_promocode(code: str) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM promocodes WHERE code = ? AND is_active = TRUE",
            (code.upper(),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def use_promocode(user_id: int, promo_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, не использовал ли уже
        cursor = await db.execute(
            "SELECT 1 FROM promo_uses WHERE user_id = ? AND promo_id = ?",
            (user_id, promo_id)
        )
        if await cursor.fetchone():
            return False
        
        await db.execute(
            "INSERT INTO promo_uses (user_id, promo_id) VALUES (?, ?)",
            (user_id, promo_id)
        )
        await db.execute(
            "UPDATE promocodes SET current_uses = current_uses + 1 WHERE id = ?",
            (promo_id,)
        )
        
        # Деактивируем если достигнут лимит
        await db.execute('''
            UPDATE promocodes SET is_active = FALSE 
            WHERE id = ? AND current_uses >= max_uses
        ''', (promo_id,))
        
        await db.commit()
        return True

async def get_all_promocodes() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM promocodes ORDER BY created_at DESC"
        )
        return [dict(row) for row in await cursor.fetchall()]

async def delete_promocode(promo_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE promocodes SET is_active = FALSE WHERE id = ?", 
            (promo_id,)
        )
        await db.commit()

def generate_promo_code(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ===== РЫНОК =====
async def create_market_item(name: str, price: int, description: str,
                             reward_type: str, reward_value: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO market_items (name, price, description, reward_type, reward_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, price, description, reward_type, reward_value))
        await db.commit()
        return cursor.lastrowid

async def get_market_items() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM market_items WHERE is_active = TRUE"
        )
        return [dict(row) for row in await cursor.fetchall()]

async def get_market_item(item_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM market_items WHERE id = ?", 
            (item_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def purchase_market_item(user_id: int, item_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO market_purchases (user_id, item_id) VALUES (?, ?)",
            (user_id, item_id)
        )
        await db.commit()
        return True

async def has_purchased_item(user_id: int, item_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM market_purchases WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        )
        return await cursor.fetchone() is not None

async def delete_market_item(item_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE market_items SET is_active = FALSE WHERE id = ?",
            (item_id,)
        )
        await db.commit()

# ===== АНКЕТЫ =====
async def create_player_profile(user_id: int, age: int, hours: str, name: str,
                                nickname: str, server: str, prev_clans: str) -> int:
    expires = datetime.now() + timedelta(days=7)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Удаляем старую анкету
        await db.execute(
            "DELETE FROM player_profiles WHERE user_id = ?", 
            (user_id,)
        )
        cursor = await db.execute('''
            INSERT INTO player_profiles 
            (user_id, age, hours_played, real_name, nickname, server, prev_clans, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, age, hours, name, nickname, server, prev_clans, expires))
        await db.commit()
        return cursor.lastrowid

async def get_active_player_profiles() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT pp.*, u.username, u.full_name, u.avatar_file_id
            FROM player_profiles pp
            JOIN users u ON pp.user_id = u.user_id
            WHERE pp.expires_at > ?
            ORDER BY pp.created_at DESC
        ''', (datetime.now(),))
        return [dict(row) for row in await cursor.fetchall()]

async def create_clan_profile(user_id: int, name: str, tag: str, avatar: str,
                              founded: str, server: str, hours: int) -> int:
    expires = datetime.now() + timedelta(days=14)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM clan_profiles WHERE user_id = ?", 
            (user_id,)
        )
        cursor = await db.execute('''
            INSERT INTO clan_profiles 
            (user_id, clan_name, clan_tag, avatar_file_id, founded_date, 
             server, hours_required, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, tag, avatar, founded, server, hours, expires))
        await db.commit()
        return cursor.lastrowid

async def get_active_clan_profiles() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT cp.*, u.username, u.full_name
            FROM clan_profiles cp
            JOIN users u ON cp.user_id = u.user_id
            WHERE cp.expires_at > ?
            ORDER BY cp.created_at DESC
        ''', (datetime.now(),))
        return [dict(row) for row in await cursor.fetchall()]

# ===== СТАТИСТИКА =====
async def get_stats() -> Dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        stats = {}
        
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_registered = TRUE")
        stats['registered_users'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM game_tasks WHERE status = 'active'"
        )
        stats['active_game_tasks'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM card_tasks WHERE status = 'active'"
        )
        stats['active_card_tasks'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM completed_tasks WHERE status = 'pending'"
        )
        stats['pending_submissions'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM withdraw_requests WHERE status = 'pending'"
        )
        stats['pending_withdrawals'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM completed_tasks WHERE status = 'completed'"
        )
        stats['total_completed'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
        stats['total_balance'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM promocodes WHERE is_active = TRUE"
        )
        stats['active_promos'] = (await cursor.fetchone())[0]
        
        return stats

# ===== ИГРОВЫЕ ЗАКАЗЫ =====
async def create_game_order(creator_id: int, category: str, resource: str,
                            amount: int, total_reward: int, executor_reward: int,
                            description: str = "") -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO game_orders 
            (creator_id, resource_category, resource_type, resource_amount,
             total_reward, executor_reward, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (creator_id, category, resource, amount, total_reward, executor_reward, description))
        await db.commit()
        return cursor.lastrowid

async def get_open_orders(page: int = 0, per_page: int = 5) -> tuple:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("SELECT COUNT(*) FROM game_orders WHERE status = 'open'")
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute('''
            SELECT go.*, u.username as creator_username, u.full_name as creator_name
            FROM game_orders go
            JOIN users u ON go.creator_id = u.user_id
            WHERE go.status = 'open'
            ORDER BY go.created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, page * per_page))
        
        return [dict(row) for row in await cursor.fetchall()], total

async def get_all_orders_admin() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT go.*, 
                   u1.username as creator_username,
                   u2.username as executor_username
            FROM game_orders go
            JOIN users u1 ON go.creator_id = u1.user_id
            LEFT JOIN users u2 ON go.executor_id = u2.user_id
            ORDER BY go.created_at DESC
            LIMIT 50
        ''')
        return [dict(row) for row in await cursor.fetchall()]

async def get_order(order_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT go.*, 
                   u1.username as creator_username, u1.full_name as creator_name,
                   u2.username as executor_username, u2.full_name as executor_name
            FROM game_orders go
            JOIN users u1 ON go.creator_id = u1.user_id
            LEFT JOIN users u2 ON go.executor_id = u2.user_id
            WHERE go.id = ?
        ''', (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def take_order(order_id: int, executor_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT creator_id, status FROM game_orders WHERE id = ?", 
            (order_id,)
        )
        row = await cursor.fetchone()
        if not row or row[1] != 'open' or row[0] == executor_id:
            return False
        
        await db.execute('''
            UPDATE game_orders 
            SET executor_id = ?, status = 'in_progress', taken_at = ?
            WHERE id = ?
        ''', (executor_id, datetime.now(), order_id))
        await db.commit()
        return True

async def complete_order(order_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM game_orders WHERE id = ?", (order_id,))
        order = await cursor.fetchone()
        if not order:
            return None
        
        await db.execute('''
            UPDATE game_orders SET status = 'completed', completed_at = ?
            WHERE id = ?
        ''', (datetime.now(), order_id))
        await db.commit()
        return dict(order)

async def cancel_order(order_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT creator_id, status, total_reward FROM game_orders WHERE id = ?",
            (order_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False
        
        creator_id, status, reward = row
        if creator_id != user_id or status not in ['open', 'in_progress']:
            return False
        
        await db.execute(
            'UPDATE users SET balance = balance + ? WHERE user_id = ?',
            (reward, creator_id)
        )
        await db.execute(
            "UPDATE game_orders SET status = 'cancelled' WHERE id = ?",
            (order_id,)
        )
        await db.commit()
        return True

async def get_user_orders(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM game_orders 
            WHERE creator_id = ? OR executor_id = ?
            ORDER BY created_at DESC LIMIT 20
        ''', (user_id, user_id))
        return [dict(row) for row in await cursor.fetchall()]

# ===== ПОДПИСКИ =====
async def get_subscription_channels() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscription_channels WHERE is_active = TRUE"
        )
        return [dict(row) for row in await cursor.fetchall()]

async def add_subscription_channel(channel_id: str, name: str, 
                                    channel_type: str = "channel") -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT OR REPLACE INTO subscription_channels (channel_id, channel_name, channel_type)
            VALUES (?, ?, ?)
        ''', (channel_id, name, channel_type))
        await db.commit()
        return cursor.lastrowid

async def remove_subscription_channel(channel_id: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE subscription_channels SET is_active = FALSE WHERE channel_id = ?",
            (channel_id,)
        )
        await db.commit()

async def get_user_subscription(user_id: int, channel_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT * FROM user_subscriptions 
            WHERE user_id = ? AND channel_id = ? AND is_active = TRUE
        ''', (user_id, channel_id))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_user_subscription(user_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT INTO user_subscriptions (user_id, channel_id)
            VALUES (?, ?)
        ''', (user_id, channel_id))
        await db.commit()

async def remove_user_subscription(user_id: int, channel_id: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE user_subscriptions SET is_active = FALSE
            WHERE user_id = ? AND channel_id = ?
        ''', (user_id, channel_id))
        await db.commit()

async def get_all_user_ids() -> List[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        return [row[0] for row in await cursor.fetchall()]
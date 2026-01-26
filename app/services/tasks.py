import aiosqlite
from datetime import datetime
from app.database.repo import tasks as task_repo
from app.config import DB_PATH, TZ

async def try_complete_task(task_id: int):
    task = await task_repo.get_task_details(task_id)
    
    if not task:
        return 0, None

    if task['status'] == 'expired':
        return -1, task['text']

    if task['status'] != 'pending':
        return 0, None

    if task['deadline']:
        try:
            deadline_dt = datetime.strptime(task['deadline'], "%Y-%m-%d %H:%M:%S")
            deadline_dt = TZ.localize(deadline_dt)
            now_dt = datetime.now(TZ)

            if now_dt > deadline_dt:
                await set_expired(task_id)
                return -1, task['text']
        except ValueError:
            pass
    
    await task_repo.mark_task_completed(task_id)
    
    reward = task['reward']
    user_id = task['assigned_to']
    await task_repo.add_bonus(user_id, reward)
    
    return reward, task['text']

async def set_expired(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE extra_tasks SET status = 'expired' WHERE id = ?", (task_id,))
        await db.commit()
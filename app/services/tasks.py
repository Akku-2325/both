import aiosqlite
from datetime import datetime
from app.core.config import DB_PATH, TZ
from app.database.repo import tasks as task_repo

async def try_complete_task(task_id: int, restaurant_id: int):
    """
    Пытается выполнить задачу.
    """
    task = await task_repo.get_task_details(task_id, restaurant_id)
    if not task:
        return 0, ""

    if task['status'] != 'pending':
        return 0, ""

    if task['deadline']:
        try:
            deadline_dt = datetime.strptime(task['deadline'], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.now(TZ).replace(tzinfo=None)

            if now_dt > deadline_dt:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE extra_tasks SET status = 'expired' WHERE id = ? AND restaurant_id = ?", 
                        (task_id, restaurant_id)
                    )
                    await db.commit()
                return -1, ""
        except ValueError:
            pass 

    await task_repo.mark_task_completed(task_id, restaurant_id)
    await task_repo.add_bonus(task['assigned_to'], restaurant_id, task['reward'])

    return task['reward'], task['text']
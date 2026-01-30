from aiogram import Router
from . import checklists, monitoring, reminders, roles, staff, tasks, invites

router = Router()

router.include_routers(
    checklists.router,
    monitoring.router,
    reminders.router,
    roles.router,
    staff.router,
    tasks.router,
    invites.router
)
from app.database.repo import users as user_repo

async def try_login(tg_id: int, restaurant_id: int, input_pin: str):
    """
    Проверяет пин-код в контексте конкретного ресторана.
    """
    if not restaurant_id:
        return None
        
    user = await user_repo.get_user(tg_id, restaurant_id)
    
    if user and user["pin_hash"] == user_repo.hash_pin(input_pin):
        if not user['is_active']:
            return "disabled"
             
        await user_repo.create_session(tg_id, restaurant_id, user["role"])
        return user
        
    return None

async def logout(tg_id: int):
    await user_repo.delete_session(tg_id)
import json
from app.database.repo import shifts as shift_repo

async def calculate_kpi(tg_id: int):
    shifts = await shift_repo.get_monthly_stats(tg_id)
    
    shifts_x = len(shifts)
    total_completed_items = 0 
    total_possible_items = 0 
    
    for s in shifts:
        try:
            data = json.loads(s['report']) if s['report'] else {}
            duties = data.get('duties', [])
            
            if not duties: continue
            
            done_count = len([d for d in duties if d['done']])
            total_count = len(duties)
            
            total_completed_items += done_count
            total_possible_items += total_count
            
        except json.JSONDecodeError:
            continue

    tasks_y_avg = round(total_completed_items / shifts_x, 1) if shifts_x > 0 else 0
    activity_score = total_completed_items 
    
    efficiency_percent = 0
    if total_possible_items > 0:
        efficiency_percent = int((total_completed_items / total_possible_items) * 100)
        
    is_eligible = efficiency_percent >= 90
    
    return {
        "shifts_x": shifts_x,
        "tasks_y_avg": tasks_y_avg,
        "activity_score": activity_score,
        "efficiency_percent": efficiency_percent,
        "is_eligible": is_eligible
    }
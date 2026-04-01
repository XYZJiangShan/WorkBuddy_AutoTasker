"""
定时调度器 - 基于 APScheduler，管理所有任务的定时执行
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable, Dict, Any, List, Optional


class TaskScheduler:
    def __init__(self, run_task_callback: Callable[[Dict[str, Any]], None]):
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._run_task = run_task_callback
        self._scheduler.start()

    def reload_all(self, tasks: List[Dict[str, Any]]):
        """根据任务列表重新注册所有定时任务"""
        self._scheduler.remove_all_jobs()
        for task in tasks:
            if not task.get("enabled", True):
                continue
            schedule = task.get("schedule")
            if not schedule:
                continue
            self._register(task, schedule)

    def _register(self, task: Dict[str, Any], schedule: Dict[str, Any]):
        stype = schedule.get("type", "cron")
        task_id = task["id"]

        try:
            if stype == "cron":
                trigger = CronTrigger(
                    day_of_week=schedule.get("day_of_week", "*"),
                    hour=schedule.get("hour", "*"),
                    minute=schedule.get("minute", "0"),
                )
            elif stype == "interval":
                trigger = IntervalTrigger(
                    hours=int(schedule.get("hours", 0)),
                    minutes=int(schedule.get("minutes", 0)),
                )
            else:
                return

            self._scheduler.add_job(
                func=self._run_task,
                trigger=trigger,
                args=[task],
                id=task_id,
                name=task.get("name", task_id),
                replace_existing=True,
                misfire_grace_time=60,
            )
        except Exception as e:
            print(f"[Scheduler] 注册任务失败 {task.get('name')}: {e}")

    def shutdown(self):
        self._scheduler.shutdown(wait=False)

    def get_next_run(self, task_id: str) -> Optional[str]:
        job = self._scheduler.get_job(task_id)
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M")
        return None


# ---- 定时配置辅助 ----
SCHEDULE_PRESETS = [
    ("不设定时", None),
    ("每天 09:00",  {"type": "cron", "hour": "9",  "minute": "0", "day_of_week": "*"}),
    ("每天 10:00",  {"type": "cron", "hour": "10", "minute": "0", "day_of_week": "*"}),
    ("每天 18:00",  {"type": "cron", "hour": "18", "minute": "0", "day_of_week": "*"}),
    ("每周一 09:00",{"type": "cron", "hour": "9",  "minute": "0", "day_of_week": "mon"}),
    ("每小时",      {"type": "interval", "hours": "1", "minutes": "0"}),
    ("每30分钟",    {"type": "interval", "hours": "0", "minutes": "30"}),
    ("自定义...",   "custom"),
]

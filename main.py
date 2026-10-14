"""Temporary testing ground: build a sample owner and print today's schedule."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_schedule(owner: Owner, schedule) -> None:
    """Print the schedule as a readable table, followed by the reasoning."""
    title = f"Today's Schedule for {owner.name} - {schedule.day:%A, %b %d %Y}"
    print(title)
    print("=" * len(title))
    print(f"{'Time':<13} {'Pet':<7} {'Task':<16} {'Min':>4}  Priority")
    print("-" * len(title))
    for item in schedule.items:
        task = item.task
        print(f"{item.start_time}-{item.end_time}   {task.pet_name:<7} "
              f"{task.title:<16} {task.duration_minutes:>4}  {task.priority}")
    print("-" * len(title))
    print(f"Planned: {schedule.total_minutes()} of {owner.available_minutes} min available")
    print()
    print(schedule.explain())


def main() -> None:
    owner = Owner("Jordan", available_minutes=90,
                  preferences={"favorite_categories": ["walk"]})

    mochi = Pet("Mochi", "dog", breed="Shiba Inu", age=3)
    luna = Pet("Luna", "cat", age=5, special_needs="daily medication")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added deliberately out of time order to exercise sort_by_time().
    luna.add_task(Task("Playtime", 20, "medium", category="enrichment",
                       preferred_time="18:30", frequency="daily"))
    mochi.add_task(Task("Morning walk", 30, "high", category="walk", frequency="daily"))
    luna.add_task(Task("Medication", 5, "high", category="meds",
                       preferred_time="09:00", frequency="daily"))
    mochi.add_task(Task("Bath", 45, "low", category="grooming", frequency="weekly"))
    mochi.add_task(Task("Breakfast", 10, "high", category="feeding",
                        preferred_time="08:00", frequency="daily"))
    luna.add_task(Task("Litter box", 10, "medium", category="cleaning",
                       preferred_time="07:15", frequency="daily"))
    mochi.add_task(Task("Brushing", 15, "low", category="grooming", frequency="weekly"))
    # Deliberate clashes to exercise conflict detection:
    # different pets at 09:00, and the same pet (Luna) at 18:30.
    mochi.add_task(Task("Ear drops", 5, "high", category="meds", preferred_time="09:00"))
    luna.add_task(Task("Brush teeth", 5, "medium", category="grooming",
                       preferred_time="18:30"))

    scheduler = Scheduler(owner)
    today = date.today()

    print("Tasks sorted by time (untimed last):")
    print_tasks(scheduler.sort_by_time(owner.get_all_tasks()))

    print("\nMarking Mochi's Breakfast (daily) and Bath (weekly) complete...")
    for title in ("Breakfast", "Bath"):
        nxt = scheduler.mark_task_complete("Mochi", title, today)
        print(f"  {title}: next occurrence due {nxt.due_date}")

    print("\nMochi's completed tasks:")
    print_tasks(scheduler.filter_by(pet_name="Mochi", completed=True))
    print("\nMochi's pending tasks:")
    print_tasks(scheduler.filter_by(pet_name="Mochi", completed=False))
    print("\nAll of Luna's tasks:")
    print_tasks(scheduler.filter_by(pet_name="Luna"))
    print()

    schedule = scheduler.generate_plan(today)
    print_schedule(owner, schedule)

    print()
    if schedule.warnings:
        print(f"WARNING: {len(schedule.warnings)} scheduling conflict(s) found:")
        for warning in schedule.warnings:
            print(f"  - {warning}")
    else:
        print("No scheduling conflicts.")


def print_tasks(tasks: list[Task]) -> None:
    """Print one line per task: time, pet, title, due date, status."""
    for t in tasks:
        status = "done" if t.completed else "pending"
        print(f"  {t.preferred_time or '--:--'}  {t.pet_name:<6} {t.title:<14} "
              f"due {t.due_date}  {status}")


if __name__ == "__main__":
    main()

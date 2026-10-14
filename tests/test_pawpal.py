"""Quick tests for core PawPal+ behaviors."""

from pawpal_system import Pet, Task


def test_mark_complete_changes_status():
    task = Task("Morning walk", 30, "high")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Breakfast", 10, "high"))

    assert len(pet.tasks) == 1
    assert pet.tasks[0].pet_name == "Mochi"


def test_sort_by_time_orders_hhmm_and_puts_untimed_last():
    from pawpal_system import Owner, Scheduler
    tasks = [Task("C", 5, "low", preferred_time="18:30"),
             Task("U", 5, "low"),
             Task("A", 5, "low", preferred_time="07:15"),
             Task("B", 5, "low", preferred_time="09:00")]
    ordered = Scheduler(Owner("J", 60)).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["A", "B", "C", "U"]


def test_filter_by_pet_and_status():
    from pawpal_system import Owner, Scheduler
    owner = Owner("J", 60)
    mochi, luna = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Walk", 30, "high", completed=True))
    mochi.add_task(Task("Feed", 10, "high"))
    luna.add_task(Task("Meds", 5, "high"))
    scheduler = Scheduler(owner)
    assert [t.title for t in scheduler.filter_by(pet_name="Mochi")] == ["Walk", "Feed"]
    assert [t.title for t in scheduler.filter_by(completed=False)] == ["Feed", "Meds"]
    assert [t.title for t in scheduler.filter_by("Mochi", completed=True)] == ["Walk"]


def test_completing_recurring_task_creates_next_occurrence():
    from datetime import date, timedelta
    from pawpal_system import Owner, Scheduler
    today = date(2026, 10, 14)
    owner = Owner("J", 60)
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("Feed", 10, "high", frequency="daily", due_date=today))
    pet.add_task(Task("Bath", 30, "low", frequency="weekly", due_date=today))
    pet.add_task(Task("Vet", 60, "high", due_date=today))
    scheduler = Scheduler(owner)

    assert scheduler.mark_task_complete("Mochi", "Feed", today).due_date == today + timedelta(days=1)
    assert scheduler.mark_task_complete("Mochi", "Bath", today).due_date == today + timedelta(weeks=1)
    assert scheduler.mark_task_complete("Mochi", "Vet", today) is None
    assert len(pet.tasks) == 5
    assert [t.title for t in pet.get_pending_tasks()] == ["Feed", "Bath"]


def test_overdue_recurring_task_next_due_is_after_today():
    from datetime import date, timedelta
    today = date(2026, 10, 14)
    task = Task("Feed", 10, "high", frequency="daily", due_date=today - timedelta(days=3))
    assert task.mark_complete(today).due_date == today + timedelta(days=1)


def _plan_with(*pets_and_tasks):
    from datetime import date
    from pawpal_system import Owner, Scheduler
    owner = Owner("J", 240)
    pets = {}
    for pet_name, task in pets_and_tasks:
        if pet_name not in pets:
            pets[pet_name] = Pet(pet_name, "dog")
            owner.add_pet(pets[pet_name])
        pets[pet_name].add_task(task)
    return Scheduler(owner).generate_plan(date.today())


def test_conflict_warns_for_same_time_different_pets():
    plan = _plan_with(("Mochi", Task("Ear drops", 5, "high", preferred_time="09:00")),
                      ("Luna", Task("Meds", 5, "high", preferred_time="09:00")))
    assert len(plan.warnings) == 1
    assert "Mochi and Luna" in plan.warnings[0]


def test_conflict_warns_for_same_pet_overlap():
    plan = _plan_with(("Luna", Task("Play", 20, "medium", preferred_time="18:30")),
                      ("Luna", Task("Teeth", 5, "medium", preferred_time="18:40")))
    assert len(plan.warnings) == 1
    assert "same pet: Luna" in plan.warnings[0]


def test_back_to_back_tasks_are_not_a_conflict():
    plan = _plan_with(("Mochi", Task("Feed", 10, "high", preferred_time="08:00")),
                      ("Mochi", Task("Walk", 30, "high", preferred_time="08:10")))
    assert plan.warnings == []


def test_invalid_time_warns_instead_of_crashing():
    plan = _plan_with(("Mochi", Task("Feed", 10, "high", preferred_time="9am")))
    assert len(plan.items) == 1
    assert "Invalid time '9am'" in plan.warnings[0]

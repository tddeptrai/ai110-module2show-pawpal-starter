"""Automated tests for core PawPal+ behaviors.

Test plan:
  1. Sorting correctness   - tasks come back in chronological / priority order.
  2. Recurrence logic      - completing a daily/weekly task creates the next one.
  3. Conflict detection    - the Scheduler flags duplicate or overlapping times.
  4. Filtering / due dates - only pending, due tasks are planned.
  5. Budget and edge cases - empty pets, time limits, bad input.
"""

from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

TODAY = date(2026, 10, 14)


def make_owner(*pets_and_tasks, minutes=240):
    """Build an Owner from (pet_name, task) pairs, creating pets as needed."""
    owner = Owner("Jordan", minutes)
    pets = {}
    for pet_name, task in pets_and_tasks:
        if pet_name not in pets:
            pets[pet_name] = Pet(pet_name, "dog")
            owner.add_pet(pets[pet_name])
        pets[pet_name].add_task(task)
    return owner


def plan_for(*pets_and_tasks, minutes=240, day=TODAY):
    """Generate a plan for the given (pet_name, task) pairs."""
    return Scheduler(make_owner(*pets_and_tasks, minutes=minutes)).generate_plan(day)


# --- Basics ------------------------------------------------------------------

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


@pytest.mark.parametrize("kwargs", [
    {"duration_minutes": 0, "priority": "high"},
    {"duration_minutes": -5, "priority": "high"},
    {"duration_minutes": 10, "priority": "urgent"},
])
def test_task_rejects_invalid_duration_or_priority(kwargs):
    with pytest.raises(ValueError):
        Task("Bad", **kwargs)


# --- 1. Sorting correctness -------------------------------------------------

def test_sort_by_time_orders_hhmm_and_puts_untimed_last():
    tasks = [Task("C", 5, "low", preferred_time="18:30"),
             Task("U", 5, "low"),
             Task("A", 5, "low", preferred_time="07:15"),
             Task("B", 5, "low", preferred_time="09:00")]
    ordered = Scheduler(Owner("J", 60)).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["A", "B", "C", "U"]


def test_sort_by_time_compares_as_clock_times_not_strings():
    # As strings "9:05" > "10:00"; as clock times it is earlier.
    tasks = [Task("Late", 5, "low", preferred_time="10:00"),
             Task("Early", 5, "low", preferred_time="9:05")]
    ordered = Scheduler(Owner("J", 60)).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["Early", "Late"]


def test_sort_by_time_keeps_original_order_for_ties_and_invalid_times():
    tasks = [Task("Bad", 5, "low", preferred_time="9am"),
             Task("First", 5, "low", preferred_time="08:00"),
             Task("Second", 5, "low", preferred_time="08:00"),
             Task("Untimed", 5, "low")]
    ordered = Scheduler(Owner("J", 60)).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["First", "Second", "Bad", "Untimed"]


def test_sort_tasks_by_priority_then_shorter_duration():
    tasks = [Task("Low", 5, "low"),
             Task("High long", 30, "high"),
             Task("Medium", 10, "medium"),
             Task("High short", 10, "high")]
    ordered = Scheduler(Owner("J", 60)).sort_tasks(tasks)
    assert [t.title for t in ordered] == ["High short", "High long", "Medium", "Low"]


def test_generated_plan_items_are_in_chronological_order():
    plan = plan_for(("Mochi", Task("Dinner", 10, "high", preferred_time="18:00")),
                    ("Mochi", Task("Walk", 30, "medium")),
                    ("Luna", Task("Meds", 5, "high", preferred_time="07:30")),
                    ("Luna", Task("Brush", 15, "low")))
    starts = [item.start_time for item in plan.items]
    assert starts == sorted(starts)
    assert plan.items[0].task.title == "Meds"


def test_flexible_task_moves_past_fixed_task_it_would_overlap():
    # Feed is fixed 08:10-08:20; a 20-minute walk can't fit in 08:00-08:10.
    plan = plan_for(("Mochi", Task("Feed", 10, "high", preferred_time="08:10")),
                    ("Mochi", Task("Walk", 20, "medium")))
    walk = next(item for item in plan.items if item.task.title == "Walk")
    assert walk.start_time == "08:20"
    assert plan.warnings == []


# --- 2. Recurrence logic ----------------------------------------------------

def test_daily_task_completion_creates_task_for_next_day():
    owner = make_owner(("Mochi", Task("Feed", 10, "high", frequency="daily", due_date=TODAY)))
    scheduler = Scheduler(owner)

    next_task = scheduler.mark_task_complete("Mochi", "Feed", TODAY)

    assert next_task.due_date == TODAY + timedelta(days=1)
    assert next_task.completed is False
    assert next_task.pet_name == "Mochi"
    assert len(owner.pets[0].tasks) == 2


def test_completing_recurring_task_creates_next_occurrence():
    owner = make_owner(("Mochi", Task("Feed", 10, "high", frequency="daily", due_date=TODAY)),
                       ("Mochi", Task("Bath", 30, "low", frequency="weekly", due_date=TODAY)),
                       ("Mochi", Task("Vet", 60, "high", due_date=TODAY)))
    pet = owner.pets[0]
    scheduler = Scheduler(owner)

    assert scheduler.mark_task_complete("Mochi", "Feed", TODAY).due_date == TODAY + timedelta(days=1)
    assert scheduler.mark_task_complete("Mochi", "Bath", TODAY).due_date == TODAY + timedelta(weeks=1)
    assert scheduler.mark_task_complete("Mochi", "Vet", TODAY) is None
    assert len(pet.tasks) == 5
    assert [t.title for t in pet.get_pending_tasks()] == ["Feed", "Bath"]


def test_next_daily_occurrence_appears_in_tomorrows_plan_not_todays():
    owner = make_owner(("Mochi", Task("Feed", 10, "high", frequency="daily", due_date=TODAY)))
    scheduler = Scheduler(owner)
    scheduler.mark_task_complete("Mochi", "Feed", TODAY)

    assert scheduler.generate_plan(TODAY).items == []
    assert [i.task.title for i in scheduler.generate_plan(TODAY + timedelta(days=1)).items] == ["Feed"]


def test_overdue_recurring_task_next_due_is_after_today():
    task = Task("Feed", 10, "high", frequency="daily", due_date=TODAY - timedelta(days=3))
    assert task.mark_complete(TODAY).due_date == TODAY + timedelta(days=1)


def test_task_completed_early_recurs_from_its_due_date():
    task = Task("Bath", 30, "low", frequency="weekly", due_date=TODAY + timedelta(days=2))
    assert task.mark_complete(TODAY).due_date == TODAY + timedelta(days=2, weeks=1)


def test_completing_daily_task_twice_in_a_row_advances_each_time():
    owner = make_owner(("Mochi", Task("Feed", 10, "high", frequency="daily", due_date=TODAY)))
    scheduler = Scheduler(owner)
    first = scheduler.mark_task_complete("Mochi", "Feed", TODAY)
    second = scheduler.mark_task_complete("Mochi", "Feed", first.due_date)
    assert second.due_date == TODAY + timedelta(days=2)
    assert len(owner.pets[0].get_pending_tasks()) == 1


def test_mark_task_complete_unknown_pet_or_task_raises():
    scheduler = Scheduler(make_owner(("Mochi", Task("Feed", 10, "high"))))
    with pytest.raises(KeyError):
        scheduler.mark_task_complete("Ghost", "Feed")
    with pytest.raises(KeyError):
        scheduler.mark_task_complete("Mochi", "Swim")


# --- 3. Conflict detection --------------------------------------------------

def test_conflict_warns_for_same_time_different_pets():
    plan = plan_for(("Mochi", Task("Ear drops", 5, "high", preferred_time="09:00")),
                    ("Luna", Task("Meds", 5, "high", preferred_time="09:00")))
    assert len(plan.warnings) == 1
    assert "Mochi and Luna" in plan.warnings[0]


def test_conflict_warns_for_duplicate_time_same_pet():
    plan = plan_for(("Mochi", Task("Feed", 10, "high", preferred_time="08:00")),
                    ("Mochi", Task("Meds", 5, "high", preferred_time="08:00")))
    assert len(plan.warnings) == 1
    assert "same pet: Mochi" in plan.warnings[0]
    # Both tasks are still in the plan; detection only warns.
    assert len(plan.items) == 2


def test_conflict_warns_for_same_pet_overlap():
    plan = plan_for(("Luna", Task("Play", 20, "medium", preferred_time="18:30")),
                    ("Luna", Task("Teeth", 5, "medium", preferred_time="18:40")))
    assert len(plan.warnings) == 1
    assert "same pet: Luna" in plan.warnings[0]


def test_three_tasks_at_same_time_report_every_pair():
    plan = plan_for(("Mochi", Task("A", 10, "high", preferred_time="12:00")),
                    ("Luna", Task("B", 10, "high", preferred_time="12:00")),
                    ("Rex", Task("C", 10, "high", preferred_time="12:00")))
    assert len(plan.warnings) == 3


def test_back_to_back_tasks_are_not_a_conflict():
    plan = plan_for(("Mochi", Task("Feed", 10, "high", preferred_time="08:00")),
                    ("Mochi", Task("Walk", 30, "high", preferred_time="08:10")))
    assert plan.warnings == []


# --- 4. Filtering and due dates ---------------------------------------------

def test_filter_by_pet_and_status():
    owner = make_owner(("Mochi", Task("Walk", 30, "high", completed=True)),
                       ("Mochi", Task("Feed", 10, "high")),
                       ("Luna", Task("Meds", 5, "high")))
    scheduler = Scheduler(owner)
    assert [t.title for t in scheduler.filter_by(pet_name="Mochi")] == ["Walk", "Feed"]
    assert [t.title for t in scheduler.filter_by(completed=False)] == ["Feed", "Meds"]
    assert [t.title for t in scheduler.filter_by("Mochi", completed=True)] == ["Walk"]
    assert scheduler.filter_by(pet_name="Ghost") == []


def test_plan_excludes_completed_and_future_tasks():
    plan = plan_for(("Mochi", Task("Done", 10, "high", completed=True, due_date=TODAY)),
                    ("Mochi", Task("Tomorrow", 10, "high", due_date=TODAY + timedelta(days=1))),
                    ("Mochi", Task("Overdue", 10, "high", due_date=TODAY - timedelta(days=1))),
                    ("Mochi", Task("Today", 10, "high", due_date=TODAY)))
    assert sorted(i.task.title for i in plan.items) == ["Overdue", "Today"]


# --- 5. Time budget and edge cases ------------------------------------------

def test_pet_with_no_tasks_gives_empty_plan():
    owner = Owner("Jordan", 60)
    owner.add_pet(Pet("Mochi", "dog"))
    plan = Scheduler(owner).generate_plan(TODAY)
    assert plan.items == [] and plan.skipped == [] and plan.warnings == []
    assert plan.explain() == "Nothing to schedule today."


def test_owner_with_no_pets_gives_empty_plan():
    plan = Scheduler(Owner("Jordan", 60)).generate_plan(TODAY)
    assert plan.items == []
    assert plan.total_minutes() == 0


def test_tasks_over_budget_are_skipped_with_reason():
    plan = plan_for(("Mochi", Task("Walk", 30, "high")),
                    ("Mochi", Task("Bath", 45, "low")),
                    minutes=40)
    assert [i.task.title for i in plan.items] == ["Walk"]
    assert [t.title for t in plan.skipped] == ["Bath"]
    assert "not enough time" in plan.skip_reasons["Mochi - Bath"]
    assert plan.total_minutes() <= 40


def test_task_exactly_filling_budget_is_scheduled():
    plan = plan_for(("Mochi", Task("Walk", 60, "high")), minutes=60)
    assert len(plan.items) == 1 and plan.skipped == []


def test_zero_minutes_available_skips_everything():
    plan = plan_for(("Mochi", Task("Walk", 10, "high")), minutes=0)
    assert plan.items == []
    assert len(plan.skipped) == 1


def test_favorite_category_wins_when_time_is_short():
    owner = make_owner(("Mochi", Task("Walk", 30, "high", category="exercise")),
                       ("Mochi", Task("Groom", 30, "high", category="grooming")),
                       minutes=30)
    owner.preferences["favorite_categories"] = ["grooming"]
    plan = Scheduler(owner).generate_plan(TODAY)
    assert [i.task.title for i in plan.items] == ["Groom"]


def test_invalid_time_warns_instead_of_crashing():
    plan = plan_for(("Mochi", Task("Feed", 10, "high", preferred_time="9am")))
    assert len(plan.items) == 1
    assert "Invalid time '9am'" in plan.warnings[0]

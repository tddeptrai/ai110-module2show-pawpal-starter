# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🛠️ Implementation Summary

All scheduling logic lives in `pawpal_system.py`. The classes are split into data, logic, and output (see `diagrams/uml.mmd`):

- **`Owner`** holds the daily time budget (`available_minutes`), preferences, and a list of **`Pet`**s.
- **`Pet`** owns its **`Task`**s and can add, edit, and remove them.
- **`Task`** is one care activity with a duration, priority, optional fixed time, and frequency. `mark_complete()` returns the next occurrence for daily/weekly tasks.
- **`Scheduler`** turns an `Owner` into a **`Schedule`** in `generate_plan()`:
  1. **Filter** to tasks that are due today and not done.
  2. **Order** them: favorite categories first, then by priority (ties go to the shorter task).
  3. **Choose** tasks in that order while they fit the remaining time; the rest are skipped with a reason.
  4. **Place** fixed-time tasks at their time, then fill the gaps with flexible tasks from 08:00.
  5. **Check** for overlapping time slots and add warnings (see Smarter Scheduling below).
- **`Schedule`** holds the placed **`ScheduledItem`**s (task + start/end time + reason), the skipped tasks, and warnings. `explain()` prints why each task was chosen or skipped.

`main.py` is a terminal demo that builds a sample owner with two pets, shows sorting, filtering, and recurring tasks, then prints today's schedule with any conflict warnings.

## 🖥️ Sample Output

`python main.py` first demos sorting, recurring tasks, and filtering, then prints the plan. Owner Jordan has 90 minutes free and two pets. Two clashes are added on purpose to show conflict warnings:

```
Today's Schedule for Jordan - Wednesday, Oct 14 2026
====================================================
Time          Pet     Task              Min  Priority
----------------------------------------------------
07:15-07:25   Luna    Litter box         10  medium
08:00-08:30   Mochi   Morning walk       30  high
08:30-08:45   Mochi   Brushing           15  low
09:00-09:05   Mochi   Ear drops           5  high
09:00-09:05   Luna    Medication          5  high
18:30-18:35   Luna    Brush teeth         5  medium
18:30-18:50   Luna    Playtime           20  medium
----------------------------------------------------
Planned: 90 of 90 min available

Why this plan:
  - Litter box (Luna): medium priority, fixed at 07:15
  - Morning walk (Mochi): high priority, fits in available time
  - Brushing (Mochi): low priority, fits in available time
  - Ear drops (Mochi): high priority, fixed at 09:00
  - Medication (Luna): high priority, fixed at 09:00
  - Brush teeth (Luna): medium priority, fixed at 18:30
  - Playtime (Luna): medium priority, fixed at 18:30
  ! Conflict (Mochi and Luna): Ear drops 09:00-09:05 overlaps Medication 09:00-09:05
  ! Conflict (same pet: Luna): Brush teeth 18:30-18:35 overlaps Playtime 18:30-18:50

WARNING: 2 scheduling conflict(s) found:
  - Conflict (Mochi and Luna): Ear drops 09:00-09:05 overlaps Medication 09:00-09:05
  - Conflict (same pet: Luna): Brush teeth 18:30-18:35 overlaps Playtime 18:30-18:50
```

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

The 32 tests in `tests/test_pawpal.py` are grouped by behavior:

- **Sorting correctness:** `sort_by_time()` returns tasks in clock order (compared as times, not strings, so `9:05` comes before `10:00`), with untimed or invalid times last and ties kept in their original order. `sort_tasks()` orders by priority, then shorter duration, and every generated plan comes out in chronological order.
- **Recurrence logic:** completing a daily task creates a new pending task due the next day (weekly tasks repeat 7 days later; one-time tasks don't repeat). The new copy appears in tomorrow's plan, not today's. Overdue or early completions don't create duplicates.
- **Conflict detection:** the Scheduler warns about duplicate times (same pet or different pets), partial overlaps, and every pair when three tasks clash. Back-to-back tasks are not flagged.
- **Filtering and due dates:** `filter_by()` works by pet and/or completion status. Completed and future tasks stay out of the plan; overdue tasks are included.
- **Edge cases:** a pet with no tasks or an owner with no pets gives an empty plan, tasks over the time budget are skipped with a reason, favorite categories win when time is short, and bad input (zero duration, unknown priority, `"9am"`) is rejected or warned about instead of crashing.

Sample test output:

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Projects\Codepath\AI110\ai110-module2show-pawpal-starter
collected 32 items

tests\test_pawpal.py ................................                    [100%]

============================= 32 passed in 0.08s ==============================
```

**Confidence Level: ⭐⭐⭐⭐ (4/5).** Every core behavior (sorting, recurrence, conflicts, filtering, time budget) is covered, including the edge cases, and all tests pass. One star is held back because the scheduler only reports conflicts instead of resolving them, and the Streamlit UI in `app.py` is checked by hand rather than by automated tests.

## 📐 Smarter Scheduling

All of these live on `Scheduler` and `Task` in `pawpal_system.py`, are exercised by `python main.py`, and are covered in `tests/test_pawpal.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_tasks()` | By "HH:MM" time (untimed last), or by priority then shortest first |
| Filtering | `Scheduler.filter_by()`, `Scheduler.filter_tasks()` | By pet name and/or completion status; by "due today" |
| Conflict handling | `Scheduler.detect_conflicts()` | Warns on overlapping time slots, for the same pet or different pets |
| Recurring tasks | `Scheduler.mark_task_complete()`, `Task.mark_complete()` | Daily tasks repeat +1 day, weekly +7 days, via `timedelta` |

**Sorting: `Scheduler.sort_by_time(tasks)`.** Returns tasks in clock order using `sorted()` with a key of `(has no usable time, minutes after midnight)`. Times are converted with `to_minutes()` rather than compared as strings, and flexible tasks (or ones with an unreadable time) go to the end. `sort_tasks()` is the ordering the planner uses: highest priority first, ties going to the shorter task.

**Filtering: `Scheduler.filter_by(pet_name=None, completed=None)`.** Returns the owner's tasks matching a pet, a completion status, or both, so `filter_by("Mochi", completed=False)` answers "what does Mochi still need?" A filter left as `None` is ignored. `filter_tasks(tasks, day)` keeps only tasks that are due and not done, and is the first step of `generate_plan()`.

**Conflict detection: `Scheduler.detect_conflicts(items)`.** After the plan is built, items are sorted by start time and each one is compared with the ones after it until a later item starts after it ends. Any overlap of the start–end ranges (not just identical start times) produces a warning that names the pets, e.g. `Conflict (same pet: Luna): Brush teeth 18:30-18:35 overlaps Playtime 18:30-18:50`. Back-to-back tasks (08:00–08:10 then 08:10–08:20) are not conflicts. It is deliberately lightweight: it never raises an error or reschedules anything. Warnings are stored in `Schedule.warnings` and shown by `Schedule.explain()`. Similarly, a task with an invalid time like `"9am"` gets a warning and is scheduled as flexible instead of crashing the plan.

**Recurring tasks: `Scheduler.mark_task_complete(pet_name, title)`.** Marks the pet's pending task done by calling `Task.mark_complete()`. For `"daily"` or `"weekly"` tasks, that returns a fresh copy due one `timedelta(days=1)` or `timedelta(weeks=1)` later, and the scheduler adds it to the same pet. The next date counts from today or the current due date, whichever is later, so an overdue task doesn't come back already overdue and a task finished early doesn't create a duplicate. One-time tasks return `None`.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

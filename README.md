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

## ✨ Features

- **Daily plan within a time budget:** picks tasks in priority order while they fit the owner's available minutes; anything that doesn't fit is skipped with a reason ("needs 45 min, only 15 min left").
- **Priority sorting with tie-breaks:** high > medium > low, and ties go to the shorter task so more care fits into the day (`Scheduler.sort_tasks`).
- **Favorite categories:** categories the owner picks (e.g. grooming) are considered first (`Scheduler.apply_preferences`).
- **Sorting by time:** tasks are listed in clock order using minutes after midnight, not string comparison, with flexible tasks last (`Scheduler.sort_by_time`).
- **Fixed-time and flexible tasks:** fixed tasks are placed at their exact time; flexible tasks fill the earliest free gap from 08:00 without overlapping them.
- **Filtering:** view tasks by pet and/or status (pending, done) with `Scheduler.filter_by`; only tasks due today and not done are planned (`Scheduler.filter_tasks`).
- **Daily and weekly recurrence:** marking a recurring task complete creates the next copy one day or one week later via `timedelta`. Overdue tasks come back due tomorrow, not already overdue (`Scheduler.mark_task_complete`).
- **Conflict warnings:** any overlapping time slots are flagged, for the same pet or between pets, without moving anything (`Scheduler.find_conflicts`, `detect_conflicts`). Back-to-back tasks are not conflicts.
- **Explained plans:** every scheduled or skipped task carries a reason, and `Schedule.explain()` prints the full "why this plan" summary.
- **Safe input handling:** zero/negative durations and unknown priorities are rejected; an unreadable time like `"9am"` produces a warning and the task is scheduled as flexible.

## 🛠️ Implementation Summary

All scheduling logic lives in `pawpal_system.py`. The classes are split into data, logic, and output (see `diagrams/uml_final.mmd`; the Phase 1 draft is `diagrams/uml.mmd`):

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

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

The 33 tests in `tests/test_pawpal.py` are grouped by behavior:

- **Sorting correctness:** `sort_by_time()` returns tasks in clock order (compared as times, not strings, so `9:05` comes before `10:00`), with untimed or invalid times last and ties kept in their original order. `sort_tasks()` orders by priority, then shorter duration, and every generated plan comes out in chronological order.
- **Recurrence logic:** completing a daily task creates a new pending task due the next day (weekly tasks repeat 7 days later; one-time tasks don't repeat). The new copy appears in tomorrow's plan, not today's. Overdue or early completions don't create duplicates.
- **Conflict detection:** the Scheduler warns about duplicate times (same pet or different pets), partial overlaps, and every pair when three tasks clash; `find_conflicts()` returns exactly the overlapping pairs. Back-to-back tasks are not flagged.
- **Filtering and due dates:** `filter_by()` works by pet and/or completion status. Completed and future tasks stay out of the plan; overdue tasks are included.
- **Edge cases:** a pet with no tasks or an owner with no pets gives an empty plan, tasks over the time budget are skipped with a reason, favorite categories win when time is short, and bad input (zero duration, unknown priority, `"9am"`) is rejected or warned about instead of crashing.

Sample test output:

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Projects\Codepath\AI110\ai110-module2show-pawpal-starter
collected 33 items

tests\test_pawpal.py .................................                   [100%]

============================= 33 passed in 0.14s ==============================
```

**Confidence Level: ⭐⭐⭐⭐ (4/5).** Every core behavior (sorting, recurrence, conflicts, filtering, time budget) is covered, including the edge cases, and all tests pass. One star is held back because the scheduler only reports conflicts instead of resolving them, and the Streamlit UI in `app.py` is checked by hand rather than by automated tests.

## 📐 Smarter Scheduling

All of these live on `Scheduler` and `Task` in `pawpal_system.py`, are exercised by `python main.py`, and are covered in `tests/test_pawpal.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_tasks()` | By "HH:MM" time (untimed last), or by priority then shortest first |
| Filtering | `Scheduler.filter_by()`, `Scheduler.filter_tasks()` | By pet name and/or completion status; by "due today" |
| Conflict handling | `Scheduler.find_conflicts()`, `Scheduler.detect_conflicts()` | Warns on overlapping time slots, for the same pet or different pets |
| Recurring tasks | `Scheduler.mark_task_complete()`, `Task.mark_complete()` | Daily tasks repeat +1 day, weekly +7 days, via `timedelta` |

**Sorting: `Scheduler.sort_by_time(tasks)`.** Returns tasks in clock order using `sorted()` with a key of `(has no usable time, minutes after midnight)`. Times are converted with `to_minutes()` rather than compared as strings, and flexible tasks (or ones with an unreadable time) go to the end. `sort_tasks()` is the ordering the planner uses: highest priority first, ties going to the shorter task.

**Filtering: `Scheduler.filter_by(pet_name=None, completed=None)`.** Returns the owner's tasks matching a pet, a completion status, or both, so `filter_by("Mochi", completed=False)` answers "what does Mochi still need?" A filter left as `None` is ignored. `filter_tasks(tasks, day)` keeps only tasks that are due and not done, and is the first step of `generate_plan()`.

**Conflict detection: `Scheduler.find_conflicts(items)` and `detect_conflicts(items)`.** After the plan is built, items are sorted by start time and each one is compared with the ones after it until a later item starts after it ends. `find_conflicts()` returns each overlapping pair (the UI uses this to flag rows), and `detect_conflicts()` turns every overlap of the start–end ranges (not just identical start times) into a warning that names the pets, e.g. `Conflict (same pet: Luna): Brush teeth 18:30-18:35 overlaps Playtime 18:30-18:50`. Back-to-back tasks (08:00–08:10 then 08:10–08:20) are not conflicts. It is deliberately lightweight: it never raises an error or reschedules anything. Warnings are stored in `Schedule.warnings` and shown by `Schedule.explain()`. Similarly, a task with an invalid time like `"9am"` gets a warning and is scheduled as flexible instead of crashing the plan.

**Recurring tasks: `Scheduler.mark_task_complete(pet_name, title)`.** Marks the pet's pending task done by calling `Task.mark_complete()`. For `"daily"` or `"weekly"` tasks, that returns a fresh copy due one `timedelta(days=1)` or `timedelta(weeks=1)` later, and the scheduler adds it to the same pet. The next date counts from today or the current due date, whichever is later, so an overdue task doesn't come back already overdue and a task finished early doesn't create a duplicate. One-time tasks return `None`.

## 📸 Demo Walkthrough

Start the app with:

```bash
streamlit run app.py
```

### Main UI features

| Section | What the user can do |
|---------|----------------------|
| **Owner** | Set their name, how many minutes they have today, and favorite task categories. |
| **Pets** | Add a pet with name, species, age, and special needs. Duplicate or blank names are rejected with an error. |
| **Tasks** | Add a task for any pet: title, duration, priority, category, frequency (once/daily/weekly), and an optional fixed time. |
| **All tasks** | See every task in one table **sorted by time** (flexible tasks last), filtered by pet and by status (Pending / Done / All). |
| **Mark a task complete** | Pick a pending task and mark it done. For a daily or weekly task, a success message shows when the next one is due, and the new copy appears in the table. |
| **Today's Schedule** | Generate the plan: summary metrics (planned time, tasks planned, conflicts), conflict warnings, the time-ordered plan table, skipped tasks, and a "Plan explanation" expander. |

### Example workflow

1. **Set up the owner.** Enter "Jordan" with 90 minutes available today.
2. **Add pets.** Add Mochi (dog) and Luna (cat).
3. **Add tasks.** For Mochi: "Morning walk" (30 min, high, flexible), "Breakfast" (10 min, high, daily, fixed at 08:00), and "Ear drops" (5 min, high, fixed at 09:00). For Luna: "Medication" (5 min, high, fixed at 09:00), "Playtime" (20 min, medium, 18:30), "Brush teeth" (5 min, medium, 18:30), and "Bath" (45 min, low, flexible).
4. **Review the task list.** The "All tasks" table shows them in clock order: Breakfast 08:00, Ear drops 09:00, Medication 09:00, Playtime and Brush teeth 18:30, then the flexible Morning walk and Bath. Switch "Show pet" to Luna to see only Luna's tasks.
5. **Generate the schedule.** Click **Generate schedule**. The metrics show 75 / 90 min planned, 6 tasks, and 2 time conflicts.
6. **Read the conflict warnings.** Above the plan, a yellow banner says "2 time conflict(s) - review these before your day starts," followed by one warning per clash in plain language, e.g. *"Luna has Brush teeth (18:30-18:35) and Playtime (18:30-18:50) at the same time. One pet can't do both, so move one of them."* The clashing rows are marked ⚠️ in the plan table. With no clashes, a green "No time conflicts" message appears instead.
7. **See what was skipped.** Bath (45 min) doesn't fit in the 15 minutes left, so an info box explains: "not enough time (needs 45 min, only 15 min left)."
8. **Complete a recurring task.** Mark "Mochi - Breakfast" complete. The app confirms "Breakfast repeats daily; next one is due Thu, Oct 15," and a pending Breakfast due tomorrow appears in the task list. The schedule refreshes and no longer includes today's Breakfast.

### Key Scheduler behaviors shown

- **Sorting:** the task list uses `sort_by_time()`; the plan picks tasks with `sort_tasks()` (priority, then shortest) and is shown in start-time order.
- **Filtering:** the task list uses `filter_by(pet_name, completed)`; the plan only includes tasks due today and not done.
- **Fixed vs. flexible placement:** Morning walk fills the first free gap after the 08:00 Breakfast (08:10-08:40).
- **Conflict warnings:** `find_conflicts()` drives the warnings and the ⚠️ rows. Conflicts are shown as warnings, not errors, because the plan is still usable and only the owner knows which task can move.
- **Recurrence:** `mark_task_complete()` adds the next daily/weekly occurrence.

### Sample CLI output

`python main.py` runs the same logic in the terminal: it sorts tasks by time, completes a daily and a weekly task, filters by pet and status, then prints today's plan. Two clashes are added on purpose to show conflict warnings.

```
Tasks sorted by time (untimed last):
  07:15  Luna   Litter box     due 2026-10-14  pending
  08:00  Mochi  Breakfast      due 2026-10-14  pending
  09:00  Mochi  Ear drops      due 2026-10-14  pending
  09:00  Luna   Medication     due 2026-10-14  pending
  18:30  Luna   Playtime       due 2026-10-14  pending
  18:30  Luna   Brush teeth    due 2026-10-14  pending
  --:--  Mochi  Morning walk   due 2026-10-14  pending
  --:--  Mochi  Bath           due 2026-10-14  pending
  --:--  Mochi  Brushing       due 2026-10-14  pending

Marking Mochi's Breakfast (daily) and Bath (weekly) complete...
  Breakfast: next occurrence due 2026-10-15
  Bath: next occurrence due 2026-10-21

Mochi's completed tasks:
  --:--  Mochi  Bath           due 2026-10-14  done
  08:00  Mochi  Breakfast      due 2026-10-14  done

Mochi's pending tasks:
  --:--  Mochi  Morning walk   due 2026-10-14  pending
  --:--  Mochi  Brushing       due 2026-10-14  pending
  09:00  Mochi  Ear drops      due 2026-10-14  pending
  08:00  Mochi  Breakfast      due 2026-10-15  pending
  --:--  Mochi  Bath           due 2026-10-21  pending

All of Luna's tasks:
  18:30  Luna   Playtime       due 2026-10-14  pending
  09:00  Luna   Medication     due 2026-10-14  pending
  07:15  Luna   Litter box     due 2026-10-14  pending
  18:30  Luna   Brush teeth    due 2026-10-14  pending

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

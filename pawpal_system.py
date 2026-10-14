"""PawPal+ core logic: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}
RECURRENCE_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def to_minutes(hhmm: str) -> int:
    """Convert "HH:MM" to minutes after midnight."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def to_hhmm(minutes: int) -> str:
    """Convert minutes after midnight to "HH:MM"."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, grooming, ...)."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    category: str = "general"
    preferred_time: str | None = None  # "HH:MM" for fixed-time tasks
    frequency: str = "once"  # "once" | "daily" | "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    pet_name: str = ""

    def __post_init__(self) -> None:
        """Reject tasks with a non-positive duration or an unknown priority."""
        if self.duration_minutes <= 0:
            raise ValueError(f"Task '{self.title}' must have a positive duration.")
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"Task '{self.title}' has invalid priority '{self.priority}'.")

    def priority_value(self) -> int:
        """Return a numeric rank for the priority (higher = more important)."""
        return PRIORITY_RANK[self.priority]

    def is_due(self, day: date) -> bool:
        """Return True if this task should be done on the given day."""
        return not self.completed and self.due_date <= day

    def mark_complete(self, today: date | None = None) -> Task | None:
        """Mark done; return the next occurrence if the task recurs.

        The next due date is one step after today, or after the current due
        date if the task was finished early, so completing a task never
        produces a duplicate that is already due.
        """
        self.completed = True
        step = RECURRENCE_STEP.get(self.frequency)
        if step is None:
            return None
        base = max(self.due_date, today or date.today())
        return replace(self, completed=False, due_date=base + step)


@dataclass
class Pet:
    """A pet and the care tasks it needs."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet."""
        task.pet_name = self.name
        self.tasks.append(task)

    def edit_task(self, title: str, **changes) -> None:
        """Update fields on the task with the given title."""
        task = self._find_task(title)
        for name, value in changes.items():
            if not hasattr(task, name):
                raise AttributeError(f"Task has no field '{name}'.")
            setattr(task, name, value)

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title."""
        self.tasks.remove(self._find_task(title))

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks that are not completed."""
        return [t for t in self.tasks if not t.completed]

    def _find_task(self, title: str) -> Task:
        """Return the task with the given title, or raise KeyError."""
        for task in self.tasks:
            if task.title == title:
                return task
        raise KeyError(f"{self.name} has no task named '{title}'.")


@dataclass
class Owner:
    """The pet owner, their daily time budget, and preferences."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove the pet with the given name."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of the owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class ScheduledItem:
    """A task placed into a time slot, with the reason it was chosen."""

    task: Task
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    reason: str = ""


@dataclass
class Schedule:
    """The generated plan for one day."""

    day: date
    items: list[ScheduledItem] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    skip_reasons: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def total_minutes(self) -> int:
        """Return the total scheduled minutes."""
        return sum(item.task.duration_minutes for item in self.items)

    def explain(self) -> str:
        """Return a human-readable explanation of the plan."""
        if not self.items and not self.skipped:
            return "Nothing to schedule today."
        lines = ["Why this plan:"]
        for item in self.items:
            lines.append(f"  - {item.task.title} ({item.task.pet_name}): {item.reason}")
        for task in self.skipped:
            key = f"{task.pet_name} - {task.title}"
            lines.append(f"  - SKIPPED {task.title} ({task.pet_name}): {self.skip_reasons[key]}")
        for warning in self.warnings:
            lines.append(f"  ! {warning}")
        return "\n".join(lines)


class Scheduler:
    """Builds a daily Schedule from an Owner's pets, tasks, and constraints."""

    def __init__(self, owner: Owner, day_start: str = "08:00") -> None:
        """Store the owner to plan for and the time the day starts."""
        self.owner = owner
        self.day_start = day_start

    def generate_plan(self, day: date) -> Schedule:
        """Filter, order, and place tasks into time slots for the given day."""
        schedule = Schedule(day=day)
        tasks = self.sort_tasks(self.apply_preferences(
            self.filter_tasks(self.owner.get_all_tasks(), day)))

        # Step 1: choose tasks that fit in the owner's available time.
        remaining = self.owner.available_minutes
        chosen = []
        for task in tasks:
            if task.duration_minutes <= remaining:
                chosen.append(task)
                remaining -= task.duration_minutes
            else:
                schedule.skipped.append(task)
                schedule.skip_reasons[f"{task.pet_name} - {task.title}"] = (
                    f"not enough time (needs {task.duration_minutes} min, "
                    f"only {remaining} min left)"
                )

        # Step 2: place fixed-time tasks first, then fill gaps with the rest.
        # A task with an unreadable time is treated as flexible (with a
        # warning) instead of crashing the whole plan.
        fixed, flexible = [], []
        for task in chosen:
            if task.preferred_time and not self._valid_time(task.preferred_time):
                schedule.warnings.append(
                    f"Invalid time '{task.preferred_time}' for {task.title} "
                    f"({task.pet_name}); scheduled as flexible instead")
            (fixed if task.preferred_time and self._valid_time(task.preferred_time)
             else flexible).append(task)

        busy: list[tuple[int, int]] = []
        for task in fixed:
            start = to_minutes(task.preferred_time)
            busy.append((start, start + task.duration_minutes))
            schedule.items.append(self._make_item(
                task, start, f"{task.priority} priority, fixed at {task.preferred_time}"))

        cursor = to_minutes(self.day_start)
        for task in flexible:
            start = self._next_free_slot(cursor, task.duration_minutes, busy)
            busy.append((start, start + task.duration_minutes))
            cursor = start + task.duration_minutes
            schedule.items.append(self._make_item(
                task, start, f"{task.priority} priority, fits in available time"))

        schedule.items.sort(key=lambda item: item.start_time)
        schedule.warnings += self.detect_conflicts(schedule.items)
        return schedule

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority, highest first; ties go to the shorter task."""
        return sorted(tasks, key=lambda t: (-t.priority_value(), t.duration_minutes))

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return a new list of tasks ordered by preferred "HH:MM" time.

        The sort key is a tuple: (has no usable time, minutes after midnight).
        False sorts before True, so timed tasks come first in clock order and
        flexible tasks (or ones with an unreadable time) go last, keeping
        their original relative order because sorted() is stable.
        """
        def key(t: Task) -> tuple[bool, int]:
            timed = bool(t.preferred_time) and self._valid_time(t.preferred_time)
            return (not timed, to_minutes(t.preferred_time) if timed else 0)
        return sorted(tasks, key=key)

    def filter_tasks(self, tasks: list[Task], day: date) -> list[Task]:
        """Keep only tasks that are due and not completed on the given day."""
        return [t for t in tasks if t.is_due(day)]

    def filter_by(self, pet_name: str | None = None,
                  completed: bool | None = None) -> list[Task]:
        """Return the owner's tasks matching a pet name and/or completion status.

        Each filter left as None is ignored, so filter_by() returns every
        task, filter_by(pet_name="Luna") returns all of Luna's tasks, and
        filter_by("Mochi", completed=False) returns what Mochi still needs.
        """
        return [t for t in self.owner.get_all_tasks()
                if (pet_name is None or t.pet_name == pet_name)
                and (completed is None or t.completed == completed)]

    def mark_task_complete(self, pet_name: str, title: str,
                           today: date | None = None) -> Task | None:
        """Complete a pet's pending task; schedule its next occurrence if it recurs.

        Only pending tasks are searched, so after a daily task has repeated
        the finished copy is never picked again. For "daily"/"weekly" tasks
        the new copy (from Task.mark_complete) is added to the same pet and
        returned; one-time tasks return None. Raises KeyError if the pet or
        pending task does not exist.
        """
        pet = next((p for p in self.owner.pets if p.name == pet_name), None)
        if pet is None:
            raise KeyError(f"No pet named '{pet_name}'.")
        task = next((t for t in pet.get_pending_tasks() if t.title == title), None)
        if task is None:
            raise KeyError(f"{pet_name} has no pending task named '{title}'.")
        next_task = task.mark_complete(today)
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def find_conflicts(self, items: list[ScheduledItem]
                       ) -> list[tuple[ScheduledItem, ScheduledItem]]:
        """Return every pair of items whose time slots overlap.

        Items are sorted by start time, so the inner loop can stop at the
        first item that starts after `first` ends. Two slots overlap when one
        starts before the other ends; back-to-back slots (08:00-08:10 then
        08:10-08:20) are not a conflict.
        """
        pairs = []
        ordered = sorted(items, key=lambda item: to_minutes(item.start_time))
        for i, first in enumerate(ordered):
            for second in ordered[i + 1:]:
                if to_minutes(second.start_time) >= to_minutes(first.end_time):
                    break
                pairs.append((first, second))
        return pairs

    def detect_conflicts(self, items: list[ScheduledItem]) -> list[str]:
        """Return a readable warning for every overlapping pair of items.

        Lightweight by design: it never raises or reschedules anything, it
        only reports, so the plan is still shown and the owner decides what
        to move.
        """
        warnings = []
        for first, second in self.find_conflicts(items):
            same_pet = first.task.pet_name == second.task.pet_name
            who = (f"same pet: {first.task.pet_name}" if same_pet
                   else f"{first.task.pet_name} and {second.task.pet_name}")
            warnings.append(
                f"Conflict ({who}): {first.task.title} "
                f"{first.start_time}-{first.end_time} overlaps "
                f"{second.task.title} {second.start_time}-{second.end_time}"
            )
        return warnings

    def apply_preferences(self, tasks: list[Task]) -> list[Task]:
        """Move tasks in the owner's favorite_categories to the front."""
        favorites = self.owner.preferences.get("favorite_categories", [])
        return sorted(tasks, key=lambda t: t.category not in favorites)

    @staticmethod
    def _valid_time(hhmm: str) -> bool:
        """Return True if hhmm is a real "HH:MM" clock time (00:00-23:59)."""
        try:
            hours, minutes = (int(part) for part in hhmm.split(":"))
        except ValueError:
            return False
        return 0 <= hours < 24 and 0 <= minutes < 60

    def _next_free_slot(self, start: int, duration: int,
                        busy: list[tuple[int, int]]) -> int:
        """Return the earliest start >= start where duration fits without overlap."""
        for busy_start, busy_end in sorted(busy):
            if start + duration <= busy_start:
                break
            if start < busy_end:
                start = busy_end
        return start

    def _make_item(self, task: Task, start: int, reason: str) -> ScheduledItem:
        """Wrap a task in a ScheduledItem starting at the given minute."""
        return ScheduledItem(task, to_hhmm(start),
                             to_hhmm(start + task.duration_minutes), reason)

"""PawPal+ core logic: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


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

    def priority_value(self) -> int:
        """Return a numeric rank for the priority (higher = more important)."""
        pass

    def is_due(self, day: date) -> bool:
        """Return True if this task should be done on the given day."""
        pass

    def mark_complete(self) -> Task | None:
        """Mark done; return the next occurrence if the task recurs."""
        pass


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
        pass

    def edit_task(self, title: str, **changes) -> None:
        """Update fields on the task with the given title."""
        pass

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title."""
        pass

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks that are not completed."""
        pass


@dataclass
class Owner:
    """The pet owner, their daily time budget, and preferences."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def remove_pet(self, pet_name: str) -> None:
        """Remove the pet with the given name."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of the owner's pets."""
        pass


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
        pass

    def explain(self) -> str:
        """Return a human-readable explanation of the plan."""
        pass


class Scheduler:
    """Builds a daily Schedule from an Owner's pets, tasks, and constraints."""

    def __init__(self, owner: Owner, day_start: str = "08:00") -> None:
        self.owner = owner
        self.day_start = day_start

    def generate_plan(self, day: date) -> Schedule:
        """Filter, order, and place tasks into time slots for the given day."""
        pass

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority (with a deterministic tie-break)."""
        pass

    def filter_tasks(self, tasks: list[Task], day: date) -> list[Task]:
        """Keep only tasks that are due and not completed on the given day."""
        pass

    def detect_conflicts(self, items: list[ScheduledItem]) -> list[str]:
        """Return warning messages for overlapping time slots."""
        pass

    def apply_preferences(self, tasks: list[Task]) -> list[Task]:
        """Adjust task ordering based on the owner's preferences."""
        pass

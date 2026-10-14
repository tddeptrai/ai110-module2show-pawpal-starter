# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

I started by writing out use cases for the app (set up an owner, add pets, add/edit tasks, generate a plan, view the reasoning, mark tasks complete) and pulled the classes out of the nouns in those scenarios. The design separates the *data* (who and what needs care) from the *logic* (how a day gets planned) and from the *output* (the plan itself). An Owner has many Pets, each Pet has many Tasks, and a Scheduler reads the Owner's constraints to produce a Schedule made of ScheduledItems.

- **Owner**: stores the owner's name, how many minutes they have available today, their preferences (e.g. "walks in the morning"), and their list of pets. It can add/remove pets and collect every task across all pets so the scheduler can plan for multiple pets at once.
- **Pet**: stores basic info (name, species, breed, age, special needs) and owns its list of care tasks. It's responsible for adding, editing, and removing tasks and returning the ones still pending.
- **Task**: one care activity with a title, duration, priority, category, optional preferred time, frequency (once/daily/weekly), completion status, and due date. It knows its own priority rank, whether it's due on a given day, and how to mark itself complete (creating the next occurrence for recurring tasks).
- **Scheduler**: the "brain" of the app. It filters out tasks that aren't due, applies owner preferences, sorts by priority, fits tasks into the available time, and detects time conflicts.
- **Schedule**: the result for one day: the scheduled items, the tasks that were skipped and why, any warnings, and an `explain()` method that turns the plan into readable reasoning.
- **ScheduledItem**: a task placed in a specific time slot (start/end time) along with the reason it was chosen. I added this so a time slot and explanation could be attached to a task without cluttering the Task class itself.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. When I turned the UML into Python class stubs, two small changes came up in the `Task` class. First, `mark_complete()` was originally drawn as returning a `Task`, but a one-time task has no next occurrence, so I changed it to return `Task | None`. Second, `preferred_time` became optional (`str | None`) because most tasks (like brushing or playtime) don't need a fixed time, and only a few (like medication at 18:00) do. Comparing the code back against the UML showed these mismatches, and I decided the code was the more accurate version, so the UML should be updated to match it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

My scheduler **warns about conflicts but does not fix them**. A task with a fixed time (like Luna's 09:00 medication) is always placed at exactly that time, even if another fixed-time task is already there. `Scheduler.detect_conflicts()` then compares the full start-to-end time ranges (not just exact start-time matches) and adds a warning such as `Conflict (Mochi and Luna): Ear drops 09:00-09:05 overlaps Medication 09:00-09:05`. Only flexible tasks get moved, into the next free gap.

I think this is reasonable because a fixed time usually means something real (meds on a schedule, a vet appointment), and the app can't know which of two clashing tasks is safe to move. Silently pushing medication to 09:05 could be worse than telling the owner. Two pets can also often be cared for at the same moment (feeding both together), so a clash is not always a real problem. The cost is that the plan can contain impossible overlaps, and the owner has to resolve them by hand.

A second, smaller tradeoff is that task selection is greedy: it takes tasks in priority order while they fit the remaining minutes. That is easy to explain ("higher priority first"), but it won't always fill the time budget perfectly. For example, it may skip a 45-minute task that would have fit if two short low-priority tasks had been dropped instead.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code throughout the project, step by step rather than all at once. First I had it read the README and generate use cases and example scenarios (normal day, not enough time, multiple pets, fixed-time meds, recurring tasks, conflicts) plus edge cases. From those it suggested the classes, and I had it turn them into a Mermaid UML diagram, then into empty Python class stubs in `pawpal_system.py`. After that it implemented the scheduling logic, wrote `main.py` to print a readable "Today's Schedule" table, and drafted the first pytest tests.

The most helpful prompts were short, specific ones tied to a single step, like "turn the suggested classes to UML" or "compare pawpal_system.py with the uml". Asking for a comparison was especially useful because it gave me a checklist of what matched and what didn't instead of just more code.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

One example: in the first set of use cases, the "not enough time" scenario was wrong. It said the 30-minute walk and the 10-minute feeding both fit in 30 minutes, which doesn't add up (40 > 30). I didn't accept that scenario as written. The corrected version made it clear that only one fits, which showed I needed to decide on a tie-break rule. I chose "higher priority first, then shorter task first."

When I asked how `detect_conflicts()` could be simplified, the AI offered a one-line version using `itertools.combinations` that checks every pair of tasks. It is shorter and more "Pythonic," but it gives up the early `break` that the sorted loop uses, and it hides the overlap rule inside a long list comprehension. A neighbour-only version (`zip(ordered, ordered[1:])`) was even shorter but wrong: it misses a long task that overlaps one two places later. I kept my original sorted loop because it is correct, easy to step through, and still fast.

I also didn't just accept the class stubs. I asked the AI to compare the code against the UML, and it found two mismatches (`mark_complete()` returning `Task | None` and `preferred_time` being optional). I decided the code was more accurate and that the UML should follow it.

To verify the logic, I ran `python main.py` and checked the output by hand: the times add up to the 90-minute budget, fixed-time tasks land at their times, Playtime moved past the 09:00 medication because it didn't fit in the 10-minute gap, and the 45-minute Bath was skipped with a reason. I also ran `python -m pytest` to confirm task completion and task addition behave correctly.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

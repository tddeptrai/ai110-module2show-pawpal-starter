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

The scheduler considers five things: **time** (the owner's `available_minutes` is a hard limit, so the plan never goes over it), **due dates and completion** (only tasks that are due today and not done are planned), **priority** (high > medium > low), **owner preferences** (favorite categories are considered first), and **fixed times** (a task like 09:00 medication is placed at exactly that time, and flexible tasks fill the gaps around it).

I ranked them by what would hurt a pet most if it went wrong. Time is a hard constraint because a plan the owner can't finish isn't useful. Priority comes next because missing medication is worse than missing brushing. Fixed times are respected as given, because a time usually means something real (meds, a vet visit). Preferences only reorder tasks, so they make the plan feel personal without overriding what the pet needs. Ties go to the shorter task so more care fits into the day.

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

**c. AI strategy**

- **Most effective features.** Letting the assistant read the whole project (README, `pawpal_system.py`, the UML, and the tests) before answering was the most useful thing, because its suggestions fit my existing classes instead of inventing new ones. Asking it to *compare* two things ("compare pawpal_system.py with the uml") gave me a checklist I could judge myself. Having it run `python main.py` and `python -m pytest` after each change meant every suggestion came with proof that it worked, and for the UI it drove the Streamlit app headlessly to check the conflict warnings and the mark-complete flow.
- **A suggestion I modified.** For the conflict check I kept my sorted loop with an early `break` instead of the AI's shorter `itertools.combinations` version, and rejected the neighbour-only `zip()` version because it misses a long task that overlaps one two slots later (details above). Later, when the UI needed to know *which* tasks clash, the options were to parse the warning strings in `app.py` or to split the method. I chose the split: `find_conflicts()` returns the overlapping pairs and `detect_conflicts()` formats them, so the UI and the CLI share one overlap rule and nothing has to parse text.
- **Separate chat sessions.** I used a separate session for each phase: design and UML, implementing the algorithms, testing, and UI plus documentation. Each session started with a clear goal and only the files it needed, so the AI's answers stayed focused (the testing session only thought about edge cases, not new features), and the commits line up with the phases (`chore: add class skeletons from UML`, `feat: implement sorting, filtering, and conflict detection`, `test: add automated test suite for PawPal+ system`).

**Being the lead architect.** The AI can produce a lot of correct-looking code very quickly, which makes it easy to lose track of the design. My job was to own the structure and the trade-offs: decide which class a feature belongs in, decide that conflicts should be warnings rather than automatic fixes, reject suggestions that were clever but harder to verify, and insist on tests and real output before accepting a change. I treated the AI like a fast junior teammate: great for drafting, but every change still needed a reason, a review against the UML, and a passing test.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

The suite in `tests/test_pawpal.py` has 33 tests grouped into five areas:

- **Sorting:** `sort_by_time()` returns clock order (including `"9:05"` before `"10:00"`, which string sorting gets wrong), puts flexible tasks last, and keeps ties in order; `sort_tasks()` orders by priority then duration; a full plan comes out in chronological order.
- **Recurrence:** completing a daily task creates a pending copy due tomorrow, which shows up in tomorrow's plan but not today's; weekly tasks repeat in 7 days; one-time tasks don't repeat; overdue and early completions don't create duplicates.
- **Conflict detection:** duplicate times (same pet or two pets), partial overlaps, three-way clashes, and back-to-back tasks (which are *not* conflicts).
- **Filtering:** by pet and status, and the plan leaves out completed and future tasks.
- **Edge cases:** a pet with no tasks, an owner with no pets, a zero-minute budget, a task that exactly fills the budget, and bad input like a zero duration or a `"9am"` time.

These matter because the scheduler's mistakes would be quiet ones. A wrong sort or an off-by-one recurrence date wouldn't crash anything; the owner would just get a plan that looks fine but is wrong, like a missed medication or a feeding listed twice. The tests pin down exact expected outputs so those mistakes get caught.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I'd give it 4 out of 5. All 33 tests pass, they cover every core behavior plus the edge cases I could think of, and the CLI demo and the Streamlit app both show the same results I checked by hand. I'm holding back one star because the Streamlit UI isn't covered by automated tests, and because conflicts are only reported, not resolved.

Next I would test: tasks that run past midnight (e.g. a 60-minute task at 23:30), a flexible task that can't fit anywhere before the end of the day, renaming a pet after tasks are added (tasks store `pet_name` as a copy), two tasks with the same title for one pet, and a full UI test of the add-pet, add-task, and mark-complete flow using Streamlit's `AppTest`.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with how the conflict warnings turned out end to end. The logic is simple and correct (it compares full time ranges, so it catches partial overlaps, not just identical start times), it's backed by tests for the tricky cases like back-to-back tasks, and in the app it shows up as something a pet owner can act on: a plain-language warning naming the pets, tasks, and times, a suggestion of what to do, and ⚠️ markers on the clashing rows. I also like that every scheduled or skipped task carries a reason, so the plan never feels like a black box.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would let the owner resolve conflicts from the UI, for example a "move to next free slot" button next to each warning, instead of only reporting them. I'd also replace the greedy task selection with one that fills the time budget better (it can skip a 45-minute task that would fit if two small low-priority tasks were dropped), and save owners, pets, and tasks to a file so the data survives closing the app. In the design, I'd give each task an ID instead of finding tasks by title, since two tasks with the same name for one pet are currently ambiguous.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

Designing first made everything after it easier. Because the UML split the data (Owner, Pet, Task), the logic (Scheduler), and the output (Schedule, ScheduledItem), every new feature had an obvious home, and the AI's suggestions could be checked against that design instead of being accepted just because they ran. The AI was fastest when I gave it one clear, small step and hardest to trust when I let it decide the structure.

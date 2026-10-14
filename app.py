from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

CATEGORIES = ["walk", "feeding", "meds", "grooming", "enrichment", "cleaning", "general"]

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan your pets' care for the day based on your time, priorities, and preferences.")

# Streamlit reruns this script on every interaction, so the Owner lives in
# session_state. It is only created the first time; later reruns reuse it.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes=90)
owner: Owner = st.session_state.owner

# --- Owner -----------------------------------------------------------------
st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = int(st.number_input(
        "Time available today (minutes)", min_value=0, max_value=1440,
        value=owner.available_minutes))
owner.preferences["favorite_categories"] = st.multiselect(
    "Favorite categories (scheduled first when priorities tie)", CATEGORIES,
    default=owner.preferences.get("favorite_categories", []))

st.divider()

# --- Pets ------------------------------------------------------------------
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age", min_value=0, max_value=40, value=1)
    special_needs = st.text_input("Special needs (optional)")
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Enter a pet name.")
        elif any(p.name == pet_name.strip() for p in owner.pets):
            st.error(f"You already have a pet named {pet_name.strip()}.")
        else:
            owner.add_pet(Pet(pet_name.strip(), species, age=int(age),
                              special_needs=special_needs))
            st.success(f"Added {pet_name.strip()}.")

if not owner.pets:
    st.info("No pets yet. Add one above.")

# --- Tasks -----------------------------------------------------------------
if owner.pets:
    st.subheader("Tasks")
    with st.form("add_task", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])
            task_title = st.text_input("Task title", value="Morning walk")
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
        fixed = st.checkbox("Must happen at a specific time")
        fixed_time = st.time_input("Time", value=None, step=300)
        if st.form_submit_button("Add task"):
            pet = next(p for p in owner.pets if p.name == pet_choice)
            if not task_title.strip():
                st.error("Enter a task title.")
            elif fixed and fixed_time is None:
                st.error("Pick a time for a fixed-time task.")
            else:
                pet.add_task(Task(
                    task_title.strip(), int(duration), priority, category=category,
                    preferred_time=fixed_time.strftime("%H:%M") if fixed else None,
                    frequency=frequency))
                st.success(f"Added '{task_title.strip()}' for {pet.name}.")

    # Task list: filtered with Scheduler.filter_by(), sorted with sort_by_time().
    st.markdown("**All tasks**")
    col1, col2 = st.columns(2)
    with col1:
        pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
    with col2:
        status_filter = st.radio("Status", ["Pending", "Done", "All"], horizontal=True)
    scheduler = Scheduler(owner)
    shown = scheduler.sort_by_time(scheduler.filter_by(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"Pending": False, "Done": True, "All": None}[status_filter]))
    if shown:
        st.caption("Sorted by time; flexible tasks are listed last.")
        st.table([
            {"Time": t.preferred_time or "flexible", "Pet": t.pet_name, "Task": t.title,
             "Minutes": t.duration_minutes, "Priority": t.priority,
             "Repeats": t.frequency, "Due": t.due_date.strftime("%b %d"),
             "Status": "done" if t.completed else "pending"}
            for t in shown
        ])
    else:
        st.caption("No tasks match these filters.")

    # Completing a daily/weekly task adds its next occurrence automatically.
    pending = scheduler.filter_by(completed=False)
    if pending:
        with st.form("complete_task"):
            labels = {f"{t.pet_name} - {t.title} (due {t.due_date:%b %d})": t for t in pending}
            choice = st.selectbox("Mark a task complete", list(labels))
            if st.form_submit_button("Mark complete"):
                task = labels[choice]
                next_task = scheduler.mark_task_complete(task.pet_name, task.title, date.today())
                # Saved in session_state so the message survives the rerun
                # that refreshes the task table above.
                st.session_state.flash = (
                    f"Done! {task.title} repeats {task.frequency}; next one is due "
                    f"{next_task.due_date:%a, %b %d}." if next_task
                    else f"Done! {task.title} was a one-time task.")
                st.rerun()
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

st.divider()

# --- Schedule --------------------------------------------------------------
st.subheader("Today's Schedule")
if st.button("Generate schedule", type="primary"):
    st.session_state.show_plan = True

# The plan is rebuilt on every rerun once requested, so it stays current
# after tasks are added or completed.
if st.session_state.get("show_plan"):
    scheduler = Scheduler(owner)
    schedule = scheduler.generate_plan(date.today())
    conflicts = scheduler.find_conflicts(schedule.items)

    if not schedule.items and not schedule.skipped:
        st.info("Nothing to schedule today. Add some tasks first.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Planned time", f"{schedule.total_minutes()} / {owner.available_minutes} min")
        col2.metric("Tasks planned", len(schedule.items))
        col3.metric("Time conflicts", len(conflicts))

        # Conflicts come first and in plain language: which pets, which
        # tasks, what time, and what to do about it. They are warnings, not
        # errors, because the plan is still usable.
        if conflicts:
            st.warning(f"**{len(conflicts)} time conflict(s)** - review these before your day starts.")
            for first, second in conflicts:
                a, b = first.task, second.task
                if a.pet_name == b.pet_name:
                    st.warning(
                        f"⏰ **{a.pet_name}** has *{a.title}* ({first.start_time}-{first.end_time}) "
                        f"and *{b.title}* ({second.start_time}-{second.end_time}) at the same time. "
                        f"One pet can't do both, so move one of them.")
                else:
                    st.warning(
                        f"⏰ *{a.title}* for **{a.pet_name}** ({first.start_time}-{first.end_time}) "
                        f"overlaps *{b.title}* for **{b.pet_name}** ({second.start_time}-{second.end_time}). "
                        f"Do them together if you can, otherwise move one.")
        else:
            st.success("✅ No time conflicts. Every task has its own time slot.")

        if schedule.items:
            clashing = {id(item) for pair in conflicts for item in pair}
            st.table([
                {"": "⚠️" if id(i) in clashing else "", "Time": f"{i.start_time}-{i.end_time}",
                 "Pet": i.task.pet_name, "Task": i.task.title, "Minutes": i.task.duration_minutes,
                 "Priority": i.task.priority, "Why": i.reason}
                for i in schedule.items
            ])

        for task in schedule.skipped:
            reason = schedule.skip_reasons[f"{task.pet_name} - {task.title}"]
            st.info(f"Skipped **{task.title}** ({task.pet_name}): {reason}")
        for warning in schedule.warnings:
            if not warning.startswith("Conflict"):
                st.warning(warning)
        with st.expander("Plan explanation"):
            st.text(schedule.explain())

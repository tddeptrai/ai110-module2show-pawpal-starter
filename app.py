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

    for pet in owner.pets:
        st.markdown(f"**{pet.name}** ({pet.species})")
        if pet.tasks:
            st.table([
                {"Task": t.title, "Minutes": t.duration_minutes, "Priority": t.priority,
                 "Category": t.category, "Time": t.preferred_time or "flexible",
                 "Frequency": t.frequency, "Done": "yes" if t.completed else ""}
                for t in pet.tasks
            ])
        else:
            st.caption("No tasks yet.")

st.divider()

# --- Schedule --------------------------------------------------------------
st.subheader("Today's Schedule")
if st.button("Generate schedule", type="primary"):
    schedule = Scheduler(owner).generate_plan(date.today())

    if not schedule.items and not schedule.skipped:
        st.info("Nothing to schedule today. Add some tasks first.")
    else:
        st.metric("Planned time", f"{schedule.total_minutes()} / {owner.available_minutes} min")
        if schedule.items:
            st.table([
                {"Time": f"{i.start_time}-{i.end_time}", "Pet": i.task.pet_name,
                 "Task": i.task.title, "Minutes": i.task.duration_minutes,
                 "Priority": i.task.priority, "Why": i.reason}
                for i in schedule.items
            ])
        for task in schedule.skipped:
            reason = schedule.skip_reasons[f"{task.pet_name} - {task.title}"]
            st.warning(f"Skipped **{task.title}** ({task.pet_name}): {reason}")
        for warning in schedule.warnings:
            st.error(warning)
        with st.expander("Plan explanation"):
            st.text(schedule.explain())

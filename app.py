from __future__ import annotations

import streamlit as st
from graphviz import Digraph

# Example DFA definition for quick loading and testing. You can modify this or create your own from scratch!
EXERCISE_STATES = "q0,q1,q2"
EXERCISE_ALPHABET = "0,1"
EXERCISE_START = "q0"
EXERCISE_ACCEPT = ["q1"]
EXERCISE_TRANSITIONS = """q0,0->q0
q0,1->q1
q1,0->q0
q1,1->q2
q2,0->q2
q2,1->q1"""
EXERCISE_STRINGS = "100,101,0001,0111,1100,01001,11001,000011"


def init_session_state() -> None:
    # Keep all widget and animation defaults in one place so reruns stay predictable.
    defaults = {
        "states_text": EXERCISE_STATES,
        "alphabet_text": EXERCISE_ALPHABET,
        "start_state": EXERCISE_START,
        "accept_states": EXERCISE_ACCEPT.copy(),
        "transition_text": EXERCISE_TRANSITIONS,
        "input_string": "101",
        "batch_strings": EXERCISE_STRINGS,
        "step_delay": 1.0,
        "animation_started": False,
        "current_step_index": -1,
        "animation_steps": [],
        "animation_final_state": None,
        "animation_accepted": False,
        "animation_message": "",
        "autoplay": False,
        "speed_preset": "Medium",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_exercise() -> None:
    st.session_state.states_text = EXERCISE_STATES
    st.session_state.alphabet_text = EXERCISE_ALPHABET
    st.session_state.start_state = EXERCISE_START
    st.session_state.accept_states = EXERCISE_ACCEPT.copy()
    st.session_state.transition_text = EXERCISE_TRANSITIONS
    st.session_state.input_string = "101"
    st.session_state.batch_strings = EXERCISE_STRINGS


def parse_csv(raw: str) -> List[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def parse_transitions(raw: str) -> Tuple[Dict[Tuple[str, str], str], List[str]]:
    transitions: Dict[Tuple[str, str], str] = {}
    errors: List[str] = []

    for line_number, line in enumerate(raw.splitlines(), start=1):
        # Ignore empty lines and comments so the transition box is easier to edit.
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "->" not in line:
            errors.append(f"Line {line_number}: missing '->'. Expected format state,symbol->next_state.")
            continue

        left, right = line.split("->", 1)
        left = left.strip()
        right = right.strip()
        if "," not in left:
            errors.append(f"Line {line_number}: missing comma on left side.")
            continue

        src, symbol = left.split(",", 1)
        src = src.strip()
        symbol = symbol.strip()
        dst = right.strip()

        if not src or not symbol or not dst:
            errors.append(f"Line {line_number}: incomplete transition.")
            continue

        key = (src, symbol)
        if key in transitions:
            errors.append(
                f"Line {line_number}: duplicate transition for ({src}, {symbol}). DFA must be deterministic."
            )
            continue

        transitions[key] = dst

    return transitions, errors


def validate_dfa(
    states: List[str],
    alphabet: List[str],
    start_state: str,
    accept_states: List[str],
    transitions: Dict[Tuple[str, str], str],
    parse_errors: List[str],
) -> List[str]:
    errors = parse_errors.copy()

    # A valid DFA needs a non-empty state set, alphabet, and a start state inside Q.
    if not states:
        errors.append("State set Q is empty.")
    if not alphabet:
        errors.append("Alphabet Sigma is empty.")
    if start_state not in states:
        errors.append("Start state q0 must belong to Q.")

    for state in accept_states:
        if state not in states:
            errors.append(f"Accept state '{state}' is not in Q.")

    for (src, symbol), dst in transitions.items():
        if src not in states:
            errors.append(f"Transition source '{src}' is not in Q.")
        if dst not in states:
            errors.append(f"Transition destination '{dst}' is not in Q.")
        if symbol not in alphabet:
            errors.append(f"Transition symbol '{symbol}' is not in Sigma.")

    for state in states:
        for symbol in alphabet:
            # Every state-symbol pair must have exactly one transition in a DFA.
            if (state, symbol) not in transitions:
                errors.append(f"Missing transition for ({state}, {symbol}).")

    return errors


def simulate(
    input_string: str,
    start_state: str,
    accept_states: List[str],
    alphabet: List[str],
    transitions: Dict[Tuple[str, str], str],
) -> Tuple[List[dict], str, bool, bool, str]:
    current = start_state
    steps: List[dict] = []

    for index, symbol in enumerate(input_string, start=1):
        # Stop immediately if the input uses a symbol outside the alphabet.
        if symbol not in alphabet:
            return (
                steps,
                current,
                False,
                False,
                f"Rejected: symbol '{symbol}' at position {index} is not in Sigma.",
            )

        # Follow the deterministic transition for the current state and symbol.
        next_state = transitions.get((current, symbol))
        if next_state is None:
            return (
                steps,
                current,
                False,
                False,
                f"Rejected: missing transition for ({current}, {symbol}).",
            )

        steps.append({"Step": index, "From": current, "Read": symbol, "To": next_state})
        current = next_state

    accepted = current in set(accept_states)
    if accepted:
        return steps, current, True, True, f"Accepted: ended in final state {current}."
    return steps, current, False, True, f"Rejected: ended in non-final state {current}."


def build_graph(
    states: List[str],
    start_state: str,
    accept_states: List[str],
    transitions: Dict[Tuple[str, str], str],
    active_state: str | None = None,
    active_edge: Tuple[str, str, str] | None = None,
) -> Digraph:
    dot = Digraph()
    dot.attr(rankdir="LR")
    dot.attr("node", shape="circle", fontsize="18")
    # Add a hidden start arrow so the initial state is visually obvious.
    dot.node("__start__", "", shape="none", width="0", height="0")

    for state in states:
        attrs = {}
        if state in accept_states:
            attrs["peripheries"] = "2"
        # Highlight the active state while the animation is running.
        if state == active_state:
            attrs["style"] = "filled"
            attrs["fillcolor"] = "#FFF4B5"
            attrs["color"] = "#C2410C"
            attrs["penwidth"] = "2.5"
        dot.node(state, state, **attrs)

    if start_state in states:
        dot.edge("__start__", start_state)

    for (src, symbol), dst in sorted(transitions.items()):
        edge_attrs = {}
        # Highlight the exact edge used in the current step.
        if active_edge == (src, symbol, dst):
            edge_attrs = {"color": "#D7263D", "fontcolor": "#D7263D", "penwidth": "3"}
        dot.edge(src, dst, label=symbol, **edge_attrs)

    return dot


def format_trace(start_state: str, steps: List[dict]) -> str:
    trace = start_state
    for step in steps:
        trace += f" -{step['Read']}-> {step['To']}"
    return trace


st.set_page_config(page_title="DFA Visualizer", layout="wide")
init_session_state()

st.title("Interactive DFA Visualizer and String Processor")
st.caption("Define a DFA quintuple, animate transitions, and test single or multiple strings.")

states = parse_csv(st.session_state.states_text)
alphabet = parse_csv(st.session_state.alphabet_text)
if not states:
    states = ["q0"]
if st.session_state.start_state not in states:
    st.session_state.start_state = states[0]
st.session_state.accept_states = [s for s in st.session_state.accept_states if s in states]

left, right = st.columns([1, 1])
with left:
    st.subheader("Define DFA quintuple (Q, \u03A3, \u03B4, q0, F)") # Unicode for Sigma and delta: "\u03A3, \u03B4"
    st.text_input("States Q (comma-separated)", key="states_text")
    st.text_input("Alphabet \u03A3 (comma-separated)", key="alphabet_text")
    st.selectbox("Start state q0", options=states, key="start_state")
    st.multiselect("Final states F", options=states, key="accept_states")
    st.text_area(
        "Transitions \u03B4, one per line: state,symbol->next_state",
        key="transition_text",
        height=220,
    )

transitions, parse_errors = parse_transitions(st.session_state.transition_text)
errors = validate_dfa(
    states=states,
    alphabet=alphabet,
    start_state=st.session_state.start_state,
    accept_states=st.session_state.accept_states,
    transitions=transitions,
    parse_errors=parse_errors,
)

with right:
    st.subheader("DFA Graph")
    if errors:
        st.error("Fix DFA definition errors before running.")
        st.write("\n".join(f"- {error}" for error in errors))
    st.graphviz_chart(
        build_graph(
            states=states,
            start_state=st.session_state.start_state,
            accept_states=st.session_state.accept_states,
            transitions=transitions,
            active_state=st.session_state.start_state,
        ),
        use_container_width=True,
    )

st.divider()
st.subheader("DFA Simulation")
st.text_input("Input string w", key="input_string")

col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    if st.button("🔨 Build & Auto-Play", use_container_width=True):
        if errors:
            st.error("Cannot run because DFA definition is invalid.")
        else:
            steps, final_state, accepted, completed, message = simulate(
                input_string=st.session_state.input_string,
                start_state=st.session_state.start_state,
                accept_states=st.session_state.accept_states,
                alphabet=alphabet,
                transitions=transitions,
            )
            st.session_state.animation_steps = steps
            st.session_state.animation_final_state = final_state
            st.session_state.animation_accepted = accepted
            st.session_state.animation_completed = completed
            st.session_state.animation_message = message
            st.session_state.animation_started = True
            st.session_state.current_step_index = -1
            st.session_state.autoplay = True
            st.rerun()

with col2:
    if st.button("⏮ Previous Step", use_container_width=True):
        if st.session_state.animation_started and st.session_state.current_step_index >= 0:
            st.session_state.current_step_index -= 1
            st.session_state.autoplay = False
            st.rerun()

with col3:
    if st.button("⏭ Next Step", use_container_width=True):
        if st.session_state.animation_started:
            if st.session_state.current_step_index < len(st.session_state.animation_steps) - 1:
                st.session_state.current_step_index += 1
                st.session_state.autoplay = False
                st.rerun()

with col4:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.animation_started = False
        st.session_state.current_step_index = -1
        st.session_state.animation_steps = []
        st.session_state.autoplay = False
        st.rerun()

speed_display_col, speed_btn1, speed_btn2, speed_btn3 = st.columns([1, 1, 1, 1])

# Render the indicator via a placeholder so it can reflect changes from this same rerun.
with speed_display_col:
    speed_indicator = st.empty()

with speed_btn1:
    if st.button("⚡ Fast", use_container_width=True, key="speed_fast"):
        st.session_state.speed_preset = "Fast"

with speed_btn2:
    if st.button("⏱ Medium", use_container_width=True, key="speed_medium"):
        st.session_state.speed_preset = "Medium"

with speed_btn3:
    if st.button("🐌 Slow", use_container_width=True, key="speed_slow"):
        st.session_state.speed_preset = "Slow"

speed_display_map = {
    "Fast": ("0.8s/step", "#FF6B6B"),
    "Medium": ("1.5s/step", "#4ECDC4"),
    "Slow": ("2.5s/step", "#95E1D3"),
}

preset_time, preset_color = speed_display_map.get(
    st.session_state.speed_preset, speed_display_map["Medium"]
)

speed_indicator.markdown(
    f"""
    <button style='width: 100%; border: 1px solid #555; border-radius: 5px; padding: 10px;
                   background-color: #0e1117; text-align: center; cursor: default; font-size: 14px;'>
        <span style='color: #aaa;'>Speed:</span> <span style='color: {preset_color}; font-weight: bold;'>{preset_time}</span>
    </button>
    """,
    unsafe_allow_html=True,
)

if st.session_state.animation_started:
    st.divider()

    steps = st.session_state.animation_steps
    current_idx = st.session_state.current_step_index

    # current_step_index == -1 means the DFA has not consumed any input yet.
    if current_idx == -1:
        current_state = st.session_state.start_state
        status_msg = f"Start at state {current_state}"
        active_edge = None
    else:
        step = steps[current_idx]
        current_state = step["To"]
        status_msg = f"Step {step['Step']}: {step['From']} --{step['Read']}--> {step['To']}"
        active_edge = (step["From"], step["Read"], step["To"])

    col_graph, col_info = st.columns([2, 1])

    with col_graph:
        st.subheader("DFA Animation")
        st.graphviz_chart(
            build_graph(
                states=states,
                start_state=st.session_state.start_state,
                accept_states=st.session_state.accept_states,
                transitions=transitions,
                active_state=current_state,
                active_edge=active_edge,
            ),
            use_container_width=True,
        )
    
    with col_info:
        st.subheader("Status")
        st.info(status_msg)

        # Progress is computed from the number of consumed symbols.
        if current_idx >= 0:
            progress = (current_idx + 1) / max(len(steps), 1)
        elif len(steps) == 0:
            progress = 1.0
        else:
            progress = 0.0
        
        st.progress(progress)
        st.metric("Step", f"{current_idx + 1} / {len(steps)}", delta=None)
    
    if current_idx >= 0:
        st.subheader("Transition Table")
        st.table(steps[: current_idx + 1])
    
    if current_idx == len(steps) - 1 or (len(steps) == 0 and current_idx == -1):
        st.divider()
        final_state = st.session_state.animation_final_state
        message = st.session_state.animation_message
        accepted = st.session_state.animation_accepted
        
        if accepted:
            st.success(message)
        else:
            st.error(message)
        
        st.write(f"**Trace:** `{format_trace(st.session_state.start_state, steps)}`")
        st.write(f"**Final state:** `{final_state}`")
    elif current_idx >= 0 and current_idx < len(steps) - 1:
        st.info("ℹ️ Click **Next Step** to continue...")
        if st.session_state.autoplay:
            # Auto-play advances one step, waits, then reruns the page.
            import time
            speed_map = {"Fast": 0.8, "Medium": 1.5, "Slow": 2.5}
            delay = speed_map.get(st.session_state.speed_preset, 1.5)
            time.sleep(delay)
            st.session_state.current_step_index += 1
            st.rerun()
    elif len(steps) > 0:
        st.info("ℹ️ Click **Next Step** to begin...")
        if st.session_state.autoplay:
            # The first auto-play tick moves from the start state to the first transition.
            import time
            speed_map = {"Fast": 0.8, "Medium": 1.5, "Slow": 2.5}
            delay = speed_map.get(st.session_state.speed_preset, 1.5)
            time.sleep(delay)
            st.session_state.current_step_index += 1
            st.rerun()

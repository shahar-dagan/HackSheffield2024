import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Set up the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File path for JSON storage
STORAGE_FILE = "data/prompt_history.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)


def load_history():
    """Load existing history from JSON file"""
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"prompts": []}


def save_to_history(prompt, svg_content):
    """Save prompt, topic plan, and SVG to JSON file"""
    history = load_history()

    new_entry = {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "topic_plan": st.session_state.get("topic_plan", ""),
        "svg_content": svg_content,
        "learning_plan": st.session_state.get("learning_plan", ""),
        "timestamp": datetime.now().isoformat(),
    }

    history["prompts"].append(new_entry)

    with open(STORAGE_FILE, "w") as f:
        json.dump(history, f, indent=2)

    return new_entry


def get_initial_questions(prompt):
    """Generate relevant questions to better understand the user's needs"""
    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher who helps break down complex topics. 
            Generate 3-4 specific questions that will help clarify what aspects of the topic the user wants to understand.
            Format your response as a JSON array of strings, containing only the questions.""",
        },
        {
            "role": "user",
            "content": f"Generate clarifying questions for someone wanting to learn about: {prompt}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.7, max_tokens=500
    )

    return json.loads(response.choices[0].message.content.strip())


# Start with the interactive learning journey
st.title("Interactive Learning Diagram Generator")

if "stage" not in st.session_state:
    st.session_state.stage = "initial"

if "questions" not in st.session_state:
    st.session_state.questions = None

if "answers" not in st.session_state:
    st.session_state.answers = []

if st.session_state.stage == "initial":
    user_prompt = st.text_area(
        "What topic would you like to learn about?",
        placeholder="Example: Neural Networks in Deep Learning",
        height=100,
    )

    if st.button("Start Learning Journey") and user_prompt:
        st.session_state.original_prompt = user_prompt
        st.session_state.questions = get_initial_questions(user_prompt)
        st.session_state.stage = "questioning"
        st.rerun()

elif st.session_state.stage == "questioning":
    st.write("### Let's understand your needs better")
    st.write(f"Topic: {st.session_state.original_prompt}")

    answers = []
    for q in st.session_state.questions:
        answer = st.text_input(q)
        answers.append(answer)

    if st.button("Generate Learning Plan") and all(answers):
        learning_plan = analyze_responses(
            st.session_state.original_prompt,
            st.session_state.questions,
            answers,
        )
        st.session_state.learning_plan = learning_plan

        # Generate the diagram
        svg_content = generate_enhanced_diagram(learning_plan)

        # Save everything to session state
        st.session_state.last_prompt = st.session_state.original_prompt
        st.session_state.last_svg = svg_content
        st.session_state.stage = "display"

        # Save to history
        save_to_history(st.session_state.original_prompt, svg_content)

        st.rerun()

elif st.session_state.stage == "display":
    st.title(st.session_state.original_prompt)

    with st.expander("📋 Learning Plan", expanded=True):
        st.write(st.session_state.learning_plan)

    col1, col2 = st.columns([3, 1])

    with col1:
        st.components.v1.html(st.session_state.last_svg, height=400)

    with col2:
        st.download_button(
            label="💾 Download SVG",
            data=st.session_state.last_svg,
            file_name="diagram.svg",
            mime="image/svg+xml",
            key="main_download",
        )

        if st.button("🔍 View SVG Source", key="main_view_source"):
            st.code(st.session_state.last_svg, language="xml")

    if st.button("Start New Topic", key="new_topic"):
        st.session_state.stage = "initial"
        st.rerun()

# Add helpful tips
with st.expander("💡 Tips for better results"):
    st.write(
        """
        - Be specific about what aspects of the topic you want to learn
        - Consider your current knowledge level when answering questions
        - Provide context about your learning goals
        - Mention any specific areas you find challenging
        """
    )

# Show history in sidebar
with st.sidebar:
    st.write("### Previous Diagrams")
    history = load_history()

    # Show most recent prompts first
    for i, entry in enumerate(reversed(history["prompts"])):
        # Get first three words of the prompt
        prompt_words = entry["prompt"].split()[:3]
        short_label = " ".join(prompt_words) + "..."

        with st.expander(f"{short_label}"):
            st.write(f"**Full prompt:** {entry['prompt']}")
            st.write(f"Created: {entry['timestamp']}")
            st.components.v1.html(entry["svg_content"], height=300)

            # Add download button for each historical entry
            st.download_button(
                label="💾 Download SVG",
                data=entry["svg_content"],
                file_name=f"diagram_{entry['id'][:8]}.svg",
                mime="image/svg+xml",
                key=f"history_download_{i}",
            )

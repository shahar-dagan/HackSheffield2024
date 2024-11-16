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

# Add this near the top of the file, after the imports
if "current_tab" not in st.session_state:
    st.session_state.current_tab = 0


def load_history():
    """Load existing history from JSON file"""
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"prompts": []}


def save_to_history(prompt, svg_content):
    """Save prompt and SVG to JSON file"""
    history = load_history()

    # Create new entry
    new_entry = {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "svg_content": svg_content,
        "timestamp": datetime.now().isoformat(),
    }

    # Add to history
    history["prompts"].append(new_entry)

    # Save to file
    with open(STORAGE_FILE, "w") as f:
        json.dump(history, f, indent=2)

    return new_entry


# Move the title and diagram display section to the top
if "last_prompt" in st.session_state and "last_svg" in st.session_state:
    st.title(st.session_state.last_prompt)

    # Create two columns for the diagram display
    col1, col2 = st.columns([3, 1])

    with col1:
        st.components.v1.html(st.session_state.last_svg, height=400)

    with col2:
        st.download_button(
            label="💾 Download SVG",
            data=st.session_state.last_svg,
            file_name="diagram.svg",
            mime="image/svg+xml",
        )

        if st.button("🔍 View SVG Source"):
            st.code(st.session_state.last_svg, language="xml")

# Move the input section to the bottom
st.write("---")  # Add a separator
st.write("Enter your prompt to generate a diagram")

# Create the search bar
user_prompt = st.text_area(
    "Enter your prompt:",
    placeholder="Example: Create a flowchart showing user authentication process",
    height=100,
)


def generate_diagram(prompt):
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful explainer and diegram creator. You will recieve instuctions to create a diagram to help explain topic. Your diagram should be infomative. You will privide it as SVD code. You will only respond with raw SVD code without formatting.",
            },
            {
                "role": "user",
                "content": f"Generate a simple diagram for: {prompt}. Respond only with the SVG code.",
            },
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using standard OpenAI model
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        svg_content = response.choices[0].message.content.strip()

        # Validate SVG
        if not svg_content.startswith("<svg") or not svg_content.endswith(
            "</svg>"
        ):
            raise ValueError("Invalid SVG generated")

        return svg_content

    except Exception as e:
        st.error(f"Error generating diagram: {str(e)}")
        return None


# Generate button
if st.button("Generate Diagram") and user_prompt:
    with st.spinner("Generating your diagram..."):
        svg_content = generate_diagram(user_prompt)

        if svg_content:
            # Save to history
            entry = save_to_history(user_prompt, svg_content)

            # Store in session state for display
            st.session_state.last_prompt = user_prompt
            st.session_state.last_svg = svg_content

            # Rerun to update the display
            st.rerun()

# Add helpful tips
with st.expander("💡 Tips for better diagrams"):
    st.write(
        """
    - Be specific about the diagram type (flowchart, sequence diagram, etc.)
    - Specify any color preferences
    - Mention key elements that should be included
    - Keep descriptions clear and concise
    """
    )

# Add history tracking
if "history" not in st.session_state:
    st.session_state.history = []

# Show history in sidebar
with st.sidebar:
    st.write("### Previous Diagrams")
    history = load_history()

    # Show most recent prompts first
    for entry in reversed(history["prompts"]):
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
            )

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


def get_number_of_topics(prompt):
    """Determine the number of topics needed for the explanation"""
    messages = [
        {
            "role": "system",
            "content": "You are to decide how many topics should be used to make up the explanation. You may choose a number in the range {1, 2, 3, 4, 5} and no other. You should respond with only a number and not any other characters.",
        },
        {
            "role": "user",
            "content": f"Read this description of the topic that the user would like to learn more about:\n{prompt}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.3, max_tokens=50
    )

    return int(response.choices[0].message.content.strip())


def plan_topics(prompt, num_topics):
    """Plan the topics for explanation"""
    messages = [
        {
            "role": "system",
            "content": "Plan and create sub sections to explain the topic. Provide a few sentences for each describing their role. Differentiate each topic with t<number>: format.",
        },
        {
            "role": "user",
            "content": f"Create {num_topics} sub sections for explaining: {prompt}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


def generate_diagram(prompt):
    """Modified to use the structured prompting approach"""
    try:
        # First, get number of topics
        num_topics = get_number_of_topics(prompt)

        # Then, get the topic plan
        topic_plan = plan_topics(prompt, num_topics)

        # For this implementation, we'll generate one combined diagram
        messages = [
            {
                "role": "system",
                "content": "You are a helpful explainer and diagram creator. Create a diagram in SVG code to help explain this topic. Respond only with raw SVG code without formatting.",
            },
            {
                "role": "user",
                "content": f"Generate a diagram for this topic plan:\n{topic_plan}\nRespond only with the SVG code.",
            },
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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

        # Store the topic plan in session state for display
        st.session_state.topic_plan = topic_plan

        return svg_content

    except Exception as e:
        st.error(f"Error generating diagram: {str(e)}")
        return None


def analyze_responses(prompt, questions, answers):
    """Analyze user's responses and create a detailed learning plan"""
    messages = [
        {
            "role": "system",
            "content": """Create a detailed learning plan based on the user's responses. 
            Structure your response in this format:
            1. Main Topic Overview
            2. Key Concepts (3-5 points)
            3. Learning Path (ordered steps)
            4. Recommended Focus Areas
            5. Diagram Type Recommendation (specify what type of diagram would work best)""",
        },
        {
            "role": "user",
            "content": f"""Original prompt: {prompt}
            Questions and Answers:
            {dict(zip(questions, answers))}""",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.7, max_tokens=1000
    )

    return response.choices[0].message.content.strip()


def generate_enhanced_diagram(learning_plan):
    """Generate a detailed diagram based on the learning plan"""
    messages = [
        {
            "role": "system",
            "content": """Create a detailed SVG diagram that visualizes this learning plan. 
            Consider using color coding, hierarchical structures, and clear visual relationships.
            Include annotations and brief explanations where relevant.
            Respond only with SVG code.""",
        },
        {
            "role": "user",
            "content": f"Create a comprehensive diagram based on this learning plan:\n{learning_plan}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.7, max_tokens=2000
    )

    return response.choices[0].message.content.strip()


# Update the main interface
st.title("Interactive Learning Diagram Generator")

# Initial prompt input
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

# Update the display section
if st.session_state.stage == "display":
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
        )

        if st.button("🔍 View SVG Source"):
            st.code(st.session_state.last_svg, language="xml")

    if st.button("Start New Topic"):
        st.session_state.stage = "initial"
        st.rerun()

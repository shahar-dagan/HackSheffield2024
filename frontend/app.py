import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
from streamlit_elements import elements, dashboard, mui, html, sync, nivo
from streamlit_agraph import agraph, Node, Edge, Config
import requests
from urllib.parse import quote
import sys
from pathlib import Path
from PIL import Image
import io
import base64
import time

# Set the page layout to wide
st.set_page_config(layout="wide")

# Load environment variables
load_dotenv()

# Set up the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File path for JSON storage
STORAGE_FILE = "data/prompt_history.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Add these helper functions right after your imports and before the main code


def get_node_size(node_type):
    """Return node size based on hierarchy"""
    return {"main": 35, "section": 30, "detail": 25}.get(node_type, 25)


def get_node_color(node_type):
    """Return visually distinct colors for different node types"""
    return {"main": "#61CDB8", "section": "#F47560", "detail": "#FED766"}.get(
        node_type, "#CCCCCC"
    )


def get_node_font(node_type):
    """Return hierarchical font styling"""
    return {
        "main": {"size": 16, "color": "black", "bold": True},
        "section": {"size": 14, "color": "black", "bold": True},
        "detail": {"size": 12, "color": "black"},
    }.get(node_type, {"size": 12, "color": "black"})


def get_border_color(node_type):
    """Return border colors for depth"""
    return {"main": "#45B69C", "section": "#D65D4A", "detail": "#E6C25D"}.get(
        node_type, "#999999"
    )


def get_node_shape(node_type):
    """Return distinct shapes for different node types"""
    return {"main": "hexagon", "section": "dot", "detail": "diamond"}.get(
        node_type, "dot"
    )


def load_history():
    """Load existing history from JSON file"""
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"topics": []}


def save_to_history(prompt, learning_plan):
    """Save topic and its learning plan to history"""
    try:
        history = load_history()

        new_entry = {
            "id": str(uuid.uuid4()),
            "prompt": prompt,
            "learning_plan": learning_plan,
            "timestamp": datetime.now().isoformat(),
        }

        if "topics" not in history:
            history["topics"] = []

        history["topics"].append(new_entry)

        with open(STORAGE_FILE, "w") as f:
            json.dump(history, f, indent=2)

        return new_entry

    except Exception as e:
        st.error(f"Error saving to history: {str(e)}")
        return None


def get_initial_questions(prompt):
    """Generate relevant questions and their multiple choice options"""
    # Check if there's LaTeX code in the session state
    latex_context = ""
    if hasattr(st.session_state, "latex_code") and st.session_state.latex_code:
        latex_context = f"\nThe topic includes this mathematical expression: {st.session_state.latex_code}"

    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher who helps understand learners' needs.
            Generate 3 relevant questions to understand what aspects of the topic the user wants to learn.
            For each question, provide 3-4 multiple choice options that are SPECIFIC to the topic.
            
            If mathematical expressions are provided, include questions about mathematical understanding and application.
            
            Format your response as a JSON array of question-option pairs.
            Example for "Machine Learning":
            [
                {
                    "question": "What aspect of Machine Learning interests you most?",
                    "options": [
                        "🤖 Supervised Learning & Classification",
                        "🧠 Neural Networks & Deep Learning",
                        "📊 Data Preprocessing & Feature Engineering",
                        "🔄 Reinforcement Learning"
                    ]
                }
            ]
            
            Make questions and options SPECIFIC to the given topic.
            Always include emojis for better visual appeal.
            Keep options concise but informative.""",
        },
        {
            "role": "user",
            "content": f"Create topic-specific questions and options for someone wanting to learn about: {prompt}{latex_context}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4", messages=messages, temperature=0.7
        )
        questions = json.loads(response.choices[0].message.content)
        return questions
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return [
            {
                "question": f"What's your current knowledge level in {prompt}?",
                "options": [
                    "🌱 Complete Beginner",
                    "📚 Some Knowledge",
                    "🎯 Intermediate",
                    "🚀 Advanced",
                ],
            },
            {
                "question": "What's your main goal with this topic?",
                "options": [
                    "📖 Understanding Core Concepts",
                    "💼 Practical Application",
                    "🔬 Deep Expertise",
                ],
            },
            {
                "question": "How do you prefer to learn?",
                "options": [
                    "🎓 Structured Theory",
                    "🛠️ Hands-on Practice",
                    "🔄 Mixed Approach",
                ],
            },
        ]


def analyze_responses(prompt, questions, answers):
    """Generate a personalized learning plan based on user responses"""
    # Include the LaTeX code in the analysis if present
    latex_context = ""
    if hasattr(st.session_state, "latex_code") and st.session_state.latex_code:
        latex_context = f"\nThe learning plan should incorporate this mathematical expression: {st.session_state.latex_code}"

    # Create a formatted string of Q&A pairs
    qa_pairs = "\n".join(
        [f"Q: {q}\nA: {a}" for q, a in zip(questions, answers)]
    )

    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher who creates detailed learning plans.
            Based on the user's topic, their responses to the clarifying questions, and any mathematical context provided,
            create a structured learning plan that includes:
            
            1. Core Concepts: List the fundamental concepts they need to understand
            2. Learning Path: Break down the topic into sequential learning steps
            3. Key Relationships: Identify important connections between concepts
            4. Practical Applications: Real-world examples or applications
            5. Common Challenges: Potential stumbling blocks and how to overcome them
            
            If mathematical expressions are provided, incorporate them into the learning plan
            and explain their significance and application.
            
            Format your response with clear headings and bullet points.
            Each section should build upon the previous one in a logical sequence.""",
        },
        {
            "role": "user",
            "content": f"""Topic: {prompt}

Clarifying Questions and Answers:
{qa_pairs}
{latex_context}

Please create a detailed learning plan based on these responses.""",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,  # Increased for more detailed responses
    )

    return response.choices[0].message.content.strip()


def convert_to_graph_data(learning_plan):
    """Convert learning plan to agraph format with improved structure"""
    nodes = []
    edges = []
    node_counter = 0

    # Split into sections and clean up
    sections = [s.strip() for s in learning_plan.split("\n\n") if s.strip()]

    # Create main topic node (first line is typically the title)
    main_title = sections[0].strip()
    main_node_id = str(node_counter)  # Convert to string without 'node_' prefix
    nodes.append(
        {
            "id": main_node_id,
            "data": {
                "title": main_title,
                "type": "main",
                "content": main_title,
            },
        }
    )
    node_counter += 1

    # Track section nodes to improve layout
    section_nodes = []

    # Process each section
    for section in sections[1:]:
        if ":" in section:
            title, content = [x.strip() for x in section.split(":", 1)]

            # Create section node
            section_node_id = str(
                node_counter
            )  # Convert to string without 'node_' prefix
            nodes.append(
                {
                    "id": section_node_id,
                    "data": {
                        "title": title,
                        "type": "section",
                        "content": title,
                    },
                }
            )
            section_nodes.append(section_node_id)
            edges.append({"source": main_node_id, "target": section_node_id})
            node_counter += 1

            # Process bullet points
            bullet_points = [
                p.strip()
                for p in content.split("\n")
                if p.strip() and p.strip().startswith(("-", "•", "*"))
            ]

            for point in bullet_points:
                point_text = point.lstrip("-•* ").strip()
                point_node_id = str(
                    node_counter
                )  # Convert to string without 'node_' prefix
                nodes.append(
                    {
                        "id": point_node_id,
                        "data": {
                            "title": point_text,
                            "type": "detail",
                            "content": point_text,
                        },
                    }
                )
                edges.append(
                    {"source": section_node_id, "target": point_node_id}
                )
                node_counter += 1

    return nodes, edges


def create_flow_component():
    """Create a custom React Flow component"""
    return """
import React from 'react';
import ReactFlow, { 
    Background, 
    Controls, 
    MiniMap,
    useNodesState,
    useEdgesState
} from 'reactflow';
import 'reactflow/dist/style.css';

const CustomNode = ({ data }) => {
    return (
        <div style={{
            background: '#fff',
            padding: '15px',
            borderRadius: '8px',
            border: '1px solid #ddd',
            maxWidth: '250px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                {data.title}
            </div>
            <div style={{ fontSize: '12px' }}>
                {data.content}
            </div>
        </div>
    );
};

const nodeTypes = {
    custom: CustomNode
};

function LearningFlow({ data }) {
    const [nodes, setNodes, onNodesChange] = useNodesState(data.nodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(data.edges);

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
            >
                <Background />
                <Controls />
                <MiniMap />
            </ReactFlow>
        </div>
    );
}

export default LearningFlow;
"""


# Add these mock data functions at the top after imports


def get_mock_questions():
    """Return mock questions with options"""
    return {
        "questions": [
            {
                "question": "What is your current level of understanding in this topic?",
                "options": [
                    "Complete beginner",
                    "Some basic knowledge",
                    "Intermediate level",
                    "Advanced practitioner",
                ],
            },
            {
                "question": "What is your primary learning goal?",
                "options": [
                    "Academic understanding",
                    "Professional application",
                    "Personal interest",
                ],
            },
            {
                "question": "How would you prefer to learn this topic?",
                "options": [
                    "Theory-first approach",
                    "Practical examples",
                    "Mix of both",
                ],
            },
        ]
    }


def get_mock_learning_plan():
    """Return a structured mock learning plan"""
    return """Machine Learning Fundamentals

Core Concepts:
Understanding the basics of machine learning, including supervised and unsupervised learning approaches. This forms the foundation of all ML applications.

Data Preprocessing:
Learn how to prepare and clean data for machine learning models. This includes handling missing values, feature scaling, and normalization techniques.

Model Selection:
Explore different types of machine learning models and when to use them. From simple linear regression to complex neural networks.

Evaluation Metrics:
Understanding how to measure model performance using various metrics like accuracy, precision, and recall.

Practical Implementation:
Hands-on experience with popular ML libraries and frameworks. Building and deploying real machine learning models."""


# Add these functions after your existing helper functions (get_node_size, get_node_color, etc.)
# but before the main display code


def ask_followup_question(topic):
    """Handle follow-up questions about a specific topic"""
    question = st.text_input(f"What would you like to know about {topic}?")

    if question and st.button("Get Answer"):
        messages = [
            {
                "role": "system",
                "content": """You are an expert teacher. Provide a clear, detailed answer
                to the user's question about a specific topic. Include examples where appropriate.""",
            },
            {
                "role": "user",
                "content": f"Topic: {topic}\nQuestion: {question}",
            },
        ]

        if st.session_state.testing_mode:
            # Mock response for testing
            answer = f"""Here's a detailed explanation about {topic} addressing your question:
            
            The key points to understand are:
            1. First important aspect
            2. Second crucial element
            3. Practical application
            
            For example, consider this real-world scenario..."""
        else:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            answer = response.choices[0].message.content.strip()

        st.write("### Answer")
        st.write(answer)


def generate_subtopic_diagram(topic, original_plan):
    """Generate a more detailed diagram for the selected subtopic"""
    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher creating detailed topic breakdowns.
            Given a topic from a learning plan, create a structured explanation with:
            
            1. Core Components: Essential elements and concepts
            2. Implementation Steps: How to learn and apply these concepts
            3. Practical Examples: Real-world applications and cases
            4. Common Challenges: Potential difficulties and solutions
            
            Format your response with clear headings and bullet points.
            Keep explanations clear and focused on this specific subtopic.""",
        },
        {
            "role": "user",
            "content": f"""From this learning plan:
            {original_plan}
            
            Create a detailed breakdown of this specific topic: {topic}""",
        },
    ]

    # Generate the subtopic plan using GPT-4
    response = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.7, max_tokens=1000
    )
    subtopic_plan = response.choices[0].message.content.strip()

    # Convert the subtopic plan to a new diagram
    try:
        nodes, edges = convert_to_graph_data(subtopic_plan)

        # Convert to agraph format
        ag_nodes = [
            Node(
                id=node["id"],
                label=wrap_text(node["data"]["title"]),
                size=get_node_size(node["data"]["type"]),
                color=get_node_color(node["data"]["type"]),
                shadow=True,
                font=get_node_font(node["data"]["type"]),
                borderWidth=2,
                borderColor=get_border_color(node["data"]["type"]),
                shape=get_node_shape(node["data"]["type"]),
            )
            for node in nodes
        ]

        ag_edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                arrow=True,
                color="#666666",
                width=2,
            )
            for edge in edges
        ]

        config = Config(
            width=2600,
            height=1400,
            directed=True,
            physics=False,
            hierarchical={
                "enabled": True,
                "levelSeparation": 600,
                "nodeSpacing": 800,
                "direction": "UD",
                "sortMethod": "directed",
                "treeSpacing": 800,
            },
            smooth=True,
            interaction={"doubleClick": False},
        )

        # Create a new section for the subtopic diagram
        st.write(f"### Detailed View: {topic}")

        # Show the text version first
        with st.expander("📝 Text Breakdown", expanded=True):
            st.markdown(subtopic_plan)

        # Then show the graph
        st.write("### Visual Breakdown")
        clicked_subnode = agraph(nodes=ag_nodes, edges=ag_edges, config=config)

        if clicked_subnode:
            handle_node_click(clicked_subnode, ag_nodes, subtopic_plan)

    except Exception as e:
        st.error(f"Error generating subtopic diagram: {str(e)}")
        # Fallback to showing just the text
        st.write(f"### Detailed Breakdown: {topic}")
        st.markdown(subtopic_plan)


def handle_node_click(node_id, nodes, learning_plan):
    """Handle click events on nodes"""
    # Find the clicked node using string ID
    clicked_node = next(
        (node for node in nodes if node.id == str(node_id)), None
    )
    if not clicked_node:
        return

    # Create a container with an anchor
    st.write(f"### 🎯 Selected Topic: {clicked_node.label}")

    # Create columns for the two options
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Expand this topic", key=f"expand_{node_id}"):
            generate_subtopic_diagram(clicked_node.label, learning_plan)

    with col2:
        if st.button("❓ Ask a question", key=f"ask_{node_id}"):
            st.session_state.show_question_input = True
            st.session_state.current_topic = clicked_node.label
            st.rerun()

    # Show question input if button was clicked
    if (
        hasattr(st.session_state, "show_question_input")
        and hasattr(st.session_state, "current_topic")
        and st.session_state.show_question_input
        and st.session_state.current_topic == clicked_node.label
    ):

        question = st.text_input(
            f"What would you like to know about {clicked_node.label}?",
            key=f"question_{node_id}",
        )

        if question and st.button("Get Answer", key=f"submit_{node_id}"):
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert teacher. Provide a clear, detailed answer
                    to the user's question about a specific topic. Include examples where appropriate.""",
                },
                {
                    "role": "user",
                    "content": f"Topic: {clicked_node.label}\nQuestion: {question}",
                },
            ]

            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            answer = response.choices[0].message.content.strip()

            st.write("### Answer")
            st.markdown(answer)


def wrap_text(text, max_chars=30):
    """Wrap long text to multiple lines"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_chars:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


def get_unsplash_image(query):
    """Get a relevant image from Unsplash API"""
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

    encoded_query = quote(query)
    url = f"https://api.unsplash.com/search/photos?query={encoded_query}&per_page=1"

    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "Accept-Version": "v1",
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                image_url = data["results"][0]["urls"]["regular"]
                photographer = data["results"][0]["user"]["name"]
                return image_url, photographer
        return None, None
    except Exception as e:
        return None, None


# Add this helper function for the copy button
def create_copy_button(text: str):
    """Create a proper Streamlit button for copying text"""
    # Create a container for the button and status message
    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("📋 Copy Code", key="copy_latex", type="primary"):
            # Store the copied status in session state
            st.session_state.copied = True

    with col2:
        if hasattr(st.session_state, "copied") and st.session_state.copied:
            st.success("Copied to clipboard!")
            # Reset the copied status after 2 seconds
            time.sleep(2)
            st.session_state.copied = False


# Modify the sidebar to remove navigation buttons
with st.sidebar:
    st.write("### Previous Topics")
    history = load_history()

    # Show most recent topics first
    for i, entry in enumerate(reversed(history.get("topics", []))):
        # Get first three words of the prompt
        prompt_words = entry["prompt"].split()[:3]
        short_label = " ".join(prompt_words) + "..."

        with st.expander(f"{short_label}"):
            st.write(f"**Topic:** {entry['prompt']}")
            st.write(f"Created: {entry['timestamp']}")
            st.write("### Learning Plan")
            st.write(entry["learning_plan"])

            # Add a button to reload this topic
            if st.button(f"Load this topic", key=f"load_{entry['id']}"):
                st.session_state.learning_plan = entry["learning_plan"]
                st.session_state.original_prompt = entry["prompt"]
                st.session_state.stage = "display"
                st.rerun()

# Add this with your other session state initializations at the start of the app
if "stage" not in st.session_state:
    st.session_state.stage = "initial"
if "questions" not in st.session_state:
    st.session_state.questions = None
if "answers" not in st.session_state:
    st.session_state.answers = []
if "testing_mode" not in st.session_state:
    st.session_state.testing_mode = False

# Remove references to current_page and directly show main content
if "stage" not in st.session_state:
    st.session_state.stage = "initial"

if "questions" not in st.session_state:
    st.session_state.questions = None

if "answers" not in st.session_state:
    st.session_state.answers = []

if st.session_state.stage == "initial":
    st.title("What would you like to learn about?")

    # Text input first
    user_prompt = st.text_area(
        label="Topic Input",
        label_visibility="collapsed",
        placeholder="Example: Machine Learning for Beginners",
        height=100,
    )

    # Optional LaTeX input
    uploaded_image_data = st.file_uploader(
        "Upload Math Image (Optional)",
        type=["png", "jpg", "jpeg"],
        help="Upload an image containing mathematical expressions to include in your learning plan",
    )

    # Process LaTeX if uploaded
    if uploaded_image_data:
        try:
            # Convert the uploaded image to base64
            image_bytes = uploaded_image_data.getvalue()
            uploaded_image = Image.open(io.BytesIO(image_bytes))

            # Display the uploaded image
            st.image(
                uploaded_image,
                caption="Uploaded Math Expression",
                use_container_width=True,
            )

            # Resize and process image for LaTeX conversion
            desired_resolution = (512, 512)
            uploaded_image = uploaded_image.resize(desired_resolution)

            # Convert to base64
            buffer = io.BytesIO()
            file_format = uploaded_image_data.type.split("/")[1].upper()
            uploaded_image.save(buffer, format=file_format)
            buffer.seek(0)
            encoded_image = base64.b64encode(buffer.read()).decode("utf-8")

            # Use the LaTeX conversion function from latex_app
            from latex_project.latex_app import convert_image_to_latex_code

            latex_code = convert_image_to_latex_code(
                encoded_image, file_format.lower()
            )

            if latex_code:
                st.session_state.latex_code = latex_code

                # Display LaTeX code with copy button
                st.markdown("### 📐 Generated LaTeX Code")
                st.markdown("```latex\n" + latex_code + "\n```")
                create_copy_button(latex_code)

                # Show preview
                st.markdown("### Preview")
                st.latex(latex_code)

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")

    # Begin button
    if st.button("Begin", type="primary") and user_prompt:
        st.session_state.original_prompt = user_prompt

        # Get and display image immediately after prompt is entered
        image_url, photographer = get_unsplash_image(user_prompt)
        if image_url:
            st.image(image_url, use_container_width=True)
            st.caption(f"📸 Photo by {photographer} on Unsplash")

        # Continue with question generation
        questions = get_initial_questions(user_prompt)
        st.session_state.questions = questions
        st.session_state.current_question = 0
        st.session_state.answers = []
        st.session_state.stage = "questioning"
        st.rerun()

elif st.session_state.stage == "questioning":
    st.title(f"Let's learn about: {st.session_state.original_prompt}")

    # Get and display image right after the title and BEFORE the questions
    image_url, photographer = get_unsplash_image(
        st.session_state.original_prompt
    )
    if image_url:
        st.image(image_url, use_container_width=True)
        st.caption(f"📸 Photo by {photographer} on Unsplash")

    # If there's LaTeX code, display it after the image
    if hasattr(st.session_state, "latex_code") and st.session_state.latex_code:
        st.markdown("### 📐 Generated LaTeX Code")

        # Display the code in a markdown block
        st.markdown("```latex\n" + st.session_state.latex_code + "\n```")

        # Add the copy button below the code block
        create_copy_button(st.session_state.latex_code)

        # Show preview if applicable
        st.markdown("### Preview")
        st.latex(st.session_state.latex_code)

    # Get current question
    current_q = st.session_state.current_question
    question = st.session_state.questions[current_q]

    # Display current question
    st.write(f"### {question['question']}")

    # Create buttons for each option
    cols = st.columns(len(question["options"]))
    for idx, (col, option) in enumerate(zip(cols, question["options"])):
        with col:
            if st.button(
                option,
                key=f"q{current_q}_opt{idx}",
                use_container_width=True,
            ):
                st.session_state.answers.append(option)

                # Move to next question or generate plan
                if current_q + 1 < len(st.session_state.questions):
                    st.session_state.current_question += 1
                else:
                    # Generate learning plan
                    learning_plan = analyze_responses(
                        st.session_state.original_prompt,
                        [q["question"] for q in st.session_state.questions],
                        st.session_state.answers,
                    )

                    # Save to history before updating session state
                    save_to_history(
                        st.session_state.original_prompt, learning_plan
                    )

                    st.session_state.learning_plan = learning_plan
                    st.session_state.stage = "display"
                st.rerun()

    # Show progress
    progress = (current_q + 1) / len(st.session_state.questions)
    st.progress(progress)

elif st.session_state.stage == "display":
    with st.container():
        st.title(st.session_state.original_prompt)

        # Get and display relevant image
        image_url, photographer = get_unsplash_image(
            st.session_state.original_prompt
        )
        if image_url:
            st.image(image_url, use_container_width=True)
            st.caption(f"📸 Photo by {photographer} on Unsplash")

        # Improve text formatting with a max-width container and better spacing
        st.markdown(
            """
            <style>
            .learning-plan-text {
                max-width: 800px;
                line-height: 1.6;
                margin: 0 auto;
                padding: 20px;
            }
            .learning-plan-text p {
                margin-bottom: 1em;
            }
            .learning-plan-text ul {
                margin-left: 20px;
                margin-bottom: 1em;
            }
            </style>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("📋 Learning Plan", expanded=True):
            st.markdown(
                f'<div class="learning-plan-text">{st.session_state.learning_plan}</div>',
                unsafe_allow_html=True,
            )

        try:
            nodes, edges = convert_to_graph_data(st.session_state.learning_plan)

            # Convert to agraph format
            ag_nodes = [
                Node(
                    id=node["id"],
                    label=wrap_text(node["data"]["title"]),
                    size=get_node_size(node["data"]["type"]),
                    color=get_node_color(node["data"]["type"]),
                    shadow=True,
                    font=get_node_font(node["data"]["type"]),
                    borderWidth=2,
                    borderColor=get_border_color(node["data"]["type"]),
                    shape=get_node_shape(node["data"]["type"]),
                )
                for node in nodes
            ]

            ag_edges = [
                Edge(
                    source=edge["source"],
                    target=edge["target"],
                    arrow=True,
                    color="#666666",
                    width=2,
                )
                for edge in edges
            ]

            config = Config(
                width=2600,
                height=1400,
                directed=True,
                physics=False,
                hierarchical={
                    "enabled": True,
                    "levelSeparation": 600,
                    "nodeSpacing": 800,
                    "direction": "UD",
                    "sortMethod": "directed",
                    "treeSpacing": 800,
                },
                smooth=True,
                interaction={"doubleClick": False},
            )

            # Render the graph
            clicked_node = agraph(nodes=ag_nodes, edges=ag_edges, config=config)

            if clicked_node:
                st.write("---")
                handle_node_click(
                    clicked_node, ag_nodes, st.session_state.learning_plan
                )

        except Exception as e:
            st.error(f"Error generating diagram: {str(e)}")
            st.write("### Learning Plan Overview")
            st.write(st.session_state.learning_plan)

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

# Remove all the elif st.session_state.current_page conditions and their content

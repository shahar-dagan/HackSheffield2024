import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
from streamlit_elements import elements, dashboard, mui, html, sync, nivo

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


def analyze_responses(prompt, questions, answers):
    """Analyze user's responses and create a detailed learning plan"""
    # Create a formatted string of Q&A pairs
    qa_pairs = "\n".join(
        [f"Q: {q}\nA: {a}" for q, a in zip(questions, answers)]
    )

    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher who creates detailed learning plans.
            Based on the user's topic and their responses to the clarifying questions,
            create a structured learning plan that includes:
            
            1. Core Concepts: List the fundamental concepts they need to understand
            2. Learning Path: Break down the topic into sequential learning steps
            3. Key Relationships: Identify important connections between concepts
            4. Practical Applications: Real-world examples or applications
            5. Common Challenges: Potential stumbling blocks and how to overcome them
            
            Format your response with clear headings and bullet points.""",
        },
        {
            "role": "user",
            "content": f"""Topic: {prompt}

Clarifying Questions and Answers:
{qa_pairs}

Please create a detailed learning plan based on these responses.""",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.7, max_tokens=1000
    )

    return response.choices[0].message.content.strip()


def convert_to_reactflow_data(learning_plan):
    """Convert learning plan to React Flow format"""
    nodes = []
    edges = []
    y_position = 0
    x_position = 400

    # Split learning plan into sections
    sections = learning_plan.split("\n\n")

    # Create main node
    nodes.append(
        {
            "id": "main",
            "type": "custom",
            "position": {"x": x_position, "y": y_position},
            "data": {"title": "Main Topic", "content": sections[0]},
        }
    )

    y_position += 150

    # Process each section
    for i, section in enumerate(sections[1:], 1):
        if section.strip():
            # Split section into title and content
            if ":" in section:
                title, content = section.split(":", 1)
            else:
                title = f"Topic {i}"
                content = section

            # Create node
            node_id = f"node-{i}"
            x_offset = (i % 3 - 1) * 300

            nodes.append(
                {
                    "id": node_id,
                    "type": "custom",
                    "position": {"x": x_position + x_offset, "y": y_position},
                    "data": {
                        "title": title.strip(),
                        "content": content.strip(),
                    },
                }
            )

            # Create edge
            edges.append(
                {
                    "id": f"edge-{i}",
                    "source": "main",
                    "target": node_id,
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#888"},
                }
            )

            # Adjust y_position for next row if needed
            if i % 3 == 0:
                y_position += 200

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
    """Return mock clarifying questions"""
    return [
        "What is your current level of understanding in this topic?",
        "What specific aspects are you most interested in?",
        "How do you plan to apply this knowledge?",
    ]


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


# Start with the interactive learning journey
st.title("Interactive Learning Diagram Generator")

if "stage" not in st.session_state:
    st.session_state.stage = "initial"

if "questions" not in st.session_state:
    st.session_state.questions = None

if "answers" not in st.session_state:
    st.session_state.answers = []

if st.session_state.stage == "initial":
    # Add a toggle for testing mode
    st.session_state.testing_mode = st.checkbox(
        "Enable Testing Mode", value=True
    )

    user_prompt = st.text_area(
        "What topic would you like to learn about?",
        placeholder="Example: Neural Networks in Deep Learning",
        height=100,
    )

    if st.button("Start Learning Journey") and user_prompt:
        st.session_state.original_prompt = user_prompt
        # Use mock questions if in testing mode
        st.session_state.questions = (
            get_mock_questions()
            if st.session_state.testing_mode
            else get_initial_questions(user_prompt)
        )
        st.session_state.stage = "questioning"
        st.rerun()

elif st.session_state.stage == "questioning":
    st.write("### Let's understand your needs better")
    st.write(f"Topic: {st.session_state.original_prompt}")

    # Add quick fill button for testing
    if st.session_state.testing_mode and st.button("Fill with Mock Answers"):
        st.session_state.learning_plan = get_mock_learning_plan()
        st.session_state.stage = "display"
        st.rerun()

    answers = []
    for q in st.session_state.questions:
        answer = st.text_input(q)
        answers.append(answer)

    if st.button("Generate Learning Plan") and all(answers):
        # Use mock data if in testing mode
        learning_plan = (
            get_mock_learning_plan()
            if st.session_state.testing_mode
            else analyze_responses(
                st.session_state.original_prompt,
                st.session_state.questions,
                answers,
            )
        )

        st.session_state.learning_plan = learning_plan
        st.session_state.last_prompt = st.session_state.original_prompt
        save_to_history(st.session_state.original_prompt, learning_plan)
        st.session_state.stage = "display"
        st.rerun()

elif st.session_state.stage == "display":
    if "learning_plan" not in st.session_state:
        st.error("No learning plan found. Please start over.")
        st.session_state.stage = "initial"
        st.rerun()

    with st.container():
        st.title(st.session_state.original_prompt)

        with st.expander("📋 Learning Plan", expanded=True):
            st.write(st.session_state.learning_plan)

        try:
            nodes, edges = convert_to_reactflow_data(
                st.session_state.learning_plan
            )

            with elements("learning_diagram"):
                layout = [dashboard.Item("diagram", 0, 0, 12, 8)]

                with dashboard.Grid(layout, draggable=False):
                    with mui.Box(
                        sx={
                            "height": "600px",
                            "width": "100%",
                            "maxWidth": "1200px",
                            "margin": "0 auto",
                            "bgcolor": "#f5f5f5",
                            "borderRadius": 2,
                            "p": 4,  # Increased padding
                            "boxShadow": 3,
                            "overflow": "auto",  # Allow scrolling if needed
                        }
                    ):
                        # Create a grid layout for nodes
                        with mui.Grid(
                            container=True,
                            spacing=3,
                            justifyContent="center",
                            alignItems="center",
                        ):
                            # Main topic node
                            with mui.Grid(item=True, xs=12):
                                mui.Paper(
                                    children=[
                                        mui.Typography(
                                            nodes[0]["data"]["title"],
                                            variant="h6",
                                            align="center",
                                            sx={"p": 2},
                                        )
                                    ],
                                    elevation=2,
                                    sx={
                                        "bgcolor": "primary.light",
                                        "color": "white",
                                        "mb": 3,
                                    },
                                )

                            # Subtopic nodes
                            for node in nodes[1:]:  # Skip the first (main) node
                                with mui.Grid(item=True, xs=12, sm=6, md=4):
                                    mui.Paper(
                                        children=[
                                            mui.Typography(
                                                node["data"]["title"],
                                                variant="subtitle1",
                                                align="center",
                                                sx={"p": 2},
                                            ),
                                            mui.Typography(
                                                node["data"]["content"],
                                                variant="body2",
                                                align="left",
                                                sx={
                                                    "p": 2,
                                                    "color": "text.secondary",
                                                },
                                            ),
                                        ],
                                        elevation=1,
                                        sx={
                                            "height": "100%",
                                            "transition": "all 0.3s",
                                            "&:hover": {
                                                "elevation": 3,
                                                "bgcolor": "action.hover",
                                            },
                                        },
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

# Show history in sidebar
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

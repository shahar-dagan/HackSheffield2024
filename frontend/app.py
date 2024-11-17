import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
from streamlit_elements import elements, dashboard, mui, html, sync, nivo
from streamlit_agraph import agraph, Node, Edge, Config

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


def convert_to_graph_data(learning_plan):
    """Convert learning plan to agraph format with improved structure"""
    nodes = []
    edges = []
    node_id = 0

    # Split into sections and clean up
    sections = [s.strip() for s in learning_plan.split("\n\n") if s.strip()]

    # Create main topic node (first line is typically the title)
    main_title = sections[0].strip()
    main_node_id = f"node_{node_id}"
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
    node_id += 1

    # Track section nodes to improve layout
    section_nodes = []

    # Process each section
    for section in sections[1:]:
        if ":" in section:
            title, content = [x.strip() for x in section.split(":", 1)]

            # Create section node
            section_node_id = f"node_{node_id}"
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
            node_id += 1

            # Process bullet points
            bullet_points = [
                p.strip()
                for p in content.split("\n")
                if p.strip() and p.strip().startswith(("-", "•", "*"))
            ]

            # Create nodes in a circular pattern around section node
            for point in bullet_points:
                point_text = point.lstrip("-•* ").strip()
                point_node_id = f"node_{node_id}"
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
                node_id += 1

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
            nodes, edges = convert_to_graph_data(st.session_state.learning_plan)

            # Convert to agraph format
            ag_nodes = [
                Node(
                    id=node["id"],
                    label=node["data"]["title"],
                    size=get_node_size(
                        node["data"]["type"]
                    ),  # Function to determine size based on type
                    color=get_node_color(
                        node["data"]["type"]
                    ),  # Function to determine color based on type
                    shadow=True,
                    font=get_node_font(
                        node["data"]["type"]
                    ),  # Function to determine font based on type
                    borderWidth=2,
                    borderColor=get_border_color(
                        node["data"]["type"]
                    ),  # Function to determine border color
                    shape=get_node_shape(
                        node["data"]["type"]
                    ),  # Function to determine shape based on type
                )
                for node in nodes
            ]

            ag_edges = [
                Edge(
                    source=edge["source"],
                    target=edge["target"],
                    # Add arrow
                    arrow=True,
                    # Style the edge
                    color="#666666",
                    width=2,
                )
                for edge in edges
            ]

            # Configure the graph
            config = Config(
                width="100%",
                height=700,  # Increased height
                directed=True,
                physics=True,
                hierarchical=True,  # Enable hierarchical layout
                smooth=True,
                physics_props={
                    "hierarchicalRepulsion": {
                        "centralGravity": 0.0,
                        "springLength": 100,
                        "springConstant": 0.01,
                        "nodeDistance": 120,
                        "damping": 0.09,
                    },
                    "solver": "hierarchicalRepulsion",
                },
                node_props={"scaling": {"min": 20, "max": 35}},
                edge_props={
                    "arrowStrikethrough": False,
                    "smooth": {"type": "cubicBezier", "roundness": 0.5},
                    "length": 250,
                },
                # Add hierarchical layout configuration
                hierarchical_props={
                    "enabled": True,
                    "levelSeparation": 150,
                    "nodeSpacing": 200,
                    "treeSpacing": 200,
                    "direction": "UD",  # Up to Down layout
                },
            )

            # Render the graph
            agraph(nodes=ag_nodes, edges=ag_edges, config=config)

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

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
            "content": """You are an expert teacher. Given a topic from a learning plan,
            create a detailed breakdown of that specific topic. Format your response with
            clear headings and bullet points, focusing only on this subtopic.""",
        },
        {
            "role": "user",
            "content": f"""From this learning plan:
            {original_plan}
            
            Create a detailed breakdown of this specific topic: {topic}""",
        },
    ]

    if st.session_state.testing_mode:
        # Mock response for testing
        subtopic_plan = f"""Detailed Breakdown: {topic}

Core Components:
- Component 1: Key details and explanation
- Component 2: Further breakdown
- Component 3: Specific elements

Implementation Steps:
- Step 1: Getting started
- Step 2: Building understanding
- Step 3: Advanced concepts

Practical Examples:
- Example 1: Real-world application
- Example 2: Case study
- Example 3: Practical scenario"""
    else:
        response = client.chat.completions.create(
            model="gpt-4", messages=messages, temperature=0.7, max_tokens=1000
        )
        subtopic_plan = response.choices[0].message.content.strip()

    # Convert the subtopic plan to a new diagram
    nodes, edges = convert_to_graph_data(subtopic_plan)

    # Create a new section for the subtopic diagram
    st.write(f"### Detailed View: {topic}")

    # Convert to agraph format and display
    ag_nodes = [
        Node(
            id=node["id"],
            label=node["data"]["title"],
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
        width="100%",
        height=500,
        directed=True,
        physics=True,
        hierarchical=True,
        smooth=True,
        interaction={"doubleClick": False},  # Disable double-click
    )

    agraph(nodes=ag_nodes, edges=ag_edges, config=config)


def handle_node_click(node_id, nodes, learning_plan):
    """Handle click events on nodes"""
    # Find the clicked node using string ID
    clicked_node = next(
        (node for node in nodes if node.id == str(node_id)), None
    )
    if not clicked_node:
        return

    # Create a container with an anchor
    interaction_container = st.container()

    # Add a header to make it clear where users landed
    interaction_container.write(f"### 🎯 Selected Topic: {clicked_node.label}")

    # Create columns for the two options
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Expand this topic"):
            generate_subtopic_diagram(clicked_node.label, learning_plan)

    with col2:
        if st.button("❓ Ask a follow-up question"):
            ask_followup_question(clicked_node.label)


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
                width="100%",
                height=700,
                directed=True,
                physics=True,
                hierarchical=True,
                smooth=True,
                interaction={"doubleClick": False},  # Disable double-click
            )

            # Render the graph
            clicked_node = agraph(nodes=ag_nodes, edges=ag_edges, config=config)

            if clicked_node:
                st.write("---")  # Add a visual separator
                handle_node_click(
                    clicked_node, ag_nodes, st.session_state.learning_plan
                )
                # Auto-scroll to the interaction section
                st.markdown(
                    f'<div id="interaction-section"></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """
                    <script>
                        document.getElementById('interaction-section').scrollIntoView();
                    </script>
                    """,
                    unsafe_allow_html=True,
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

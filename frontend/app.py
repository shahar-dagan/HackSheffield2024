import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
from streamlit_elements import elements, dashboard, mui, html, sync, nivo
from streamlit_agraph import agraph, Node, Edge, Config

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
    messages = [
        {
            "role": "system",
            "content": """You are an expert teacher who helps understand learners' needs.
            Generate 3 relevant questions to understand what aspects of the topic the user wants to learn.
            For each question, provide 3-4 multiple choice options that are SPECIFIC to the topic.
            
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
                },
                {
                    "question": "Which ML application area is most relevant to you?",
                    "options": [
                        "📱 Mobile & Edge Applications",
                        "💻 Enterprise Software",
                        "🔬 Research & Academia"
                    ]
                }
            ]
            
            Make questions and options SPECIFIC to the given topic.
            Always include emojis for better visual appeal.
            Keep options concise but informative.""",
        },
        {
            "role": "user",
            "content": f"Create topic-specific questions and options for someone wanting to learn about: {prompt}",
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
        # Fallback to generic questions if generation fails
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

    # Create a new section for the subtopic diagram
    st.write(f"### Detailed View: {topic}")

    with st.container():
        clicked_node = agraph(
            nodes=ag_nodes,
            edges=ag_edges,
            config=Config(
                width="100%",
                height=700,
                directed=True,
                physics=True,
                hierarchical=True,
                smooth=True,
                interaction={"doubleClick": False},
            ),
        )

        if clicked_node:
            st.write("---")
            handle_node_click(clicked_node, ag_nodes, subtopic_plan)


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


if "stage" not in st.session_state:
    st.session_state.stage = "initial"

if "questions" not in st.session_state:
    st.session_state.questions = None

if "answers" not in st.session_state:
    st.session_state.answers = []

if st.session_state.stage == "initial":
    st.title("What would you like to learn about?")

    user_prompt = st.text_area(
        "",  # No label, keeping it clean
        placeholder="Example: Machine Learning for Beginners",
        height=100,
    )

    if (
        st.button("Begin", type="primary") and user_prompt
    ):  # Primary button for emphasis
        # Store the original prompt
        st.session_state.original_prompt = user_prompt
        # Get customized questions based on the topic
        questions = get_initial_questions(user_prompt)
        st.session_state.questions = questions
        st.session_state.current_question = 0  # Track which question we're on
        st.session_state.answers = []  # Store answers
        st.session_state.stage = "questioning"
        st.rerun()

elif st.session_state.stage == "questioning":
    st.title(f"Let's learn about: {st.session_state.original_prompt}")

    current_q = st.session_state.current_question
    question = st.session_state.questions[current_q]

    # Display current question
    st.write(f"### {question['question']}")

    # Create buttons for each option
    cols = st.columns(len(question["options"]))
    for idx, (col, option) in enumerate(zip(cols, question["options"])):
        with col:
            if st.button(
                option, key=f"q{current_q}_opt{idx}", use_container_width=True
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
    if "learning_plan" not in st.session_state:
        st.error("No learning plan found. Please start over.")
        st.session_state.stage = "initial"
        st.rerun()

    with st.container():
        st.title(st.session_state.original_prompt)

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

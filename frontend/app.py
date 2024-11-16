import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid
import streamlit.components.v1 as components

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


def create_d3_diagram_data(learning_plan):
    """Convert learning plan into D3 hierarchical format"""
    messages = [
        {
            "role": "system",
            "content": """Convert the learning plan into a clear hierarchical diagram structure.
            Output only valid JSON in this exact format:
            {
                "name": "Main Topic",
                "children": [
                    {
                        "name": "Core Concept 1",
                        "description": "Clear explanation of this concept",
                        "children": [
                            {
                                "name": "Subtopic 1.1",
                                "description": "Detailed explanation"
                            }
                        ]
                    }
                ]
            }
            Focus on making each concept clear and well-structured.""",
        },
        {
            "role": "user",
            "content": f"Convert this learning plan into a diagram structure:\n{learning_plan}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        # Clean up any markdown formatting
        content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as e:
        # Provide a simple fallback structure
        return {
            "name": "Learning Plan",
            "children": [
                {
                    "name": "Key Concepts",
                    "description": "Main ideas and fundamentals",
                    "children": [
                        {
                            "name": "Getting Started",
                            "description": "Basic concepts and foundations",
                        }
                    ],
                }
            ],
        }


def create_interactive_diagram():
    """Create an interactive D3.js diagram"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            .node {
                cursor: pointer;
            }
            .node circle {
                fill: #fff;
                stroke: steelblue;
                stroke-width: 3px;
            }
            .node text {
                font: 12px sans-serif;
            }
            .link {
                fill: none;
                stroke: #ccc;
                stroke-width: 2px;
            }
            .tooltip {
                position: absolute;
                background: white;
                border: 1px solid #ddd;
                padding: 10px;
                border-radius: 5px;
                display: none;
            }
            .question-form {
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: white;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div id="diagram"></div>
        <div class="tooltip"></div>
        <div class="question-form">
            <input type="text" id="question" placeholder="Ask a question about this topic...">
            <button onclick="askQuestion()">Ask</button>
        </div>
        <script>
            // D3.js visualization code here
            const data = DIAGRAM_DATA;  // This will be replaced with actual data
            
            const width = 800;
            const height = 600;
            
            const tree = d3.tree().size([height, width - 160]);
            
            const root = d3.hierarchy(data);
            
            const svg = d3.select("#diagram")
                .append("svg")
                .attr("width", width)
                .attr("height", height)
                .append("g")
                .attr("transform", "translate(80,0)");
            
            const link = svg.selectAll(".link")
                .data(tree(root).links())
                .enter().append("path")
                .attr("class", "link")
                .attr("d", d3.linkHorizontal()
                    .x(d => d.y)
                    .y(d => d.x));
            
            const node = svg.selectAll(".node")
                .data(root.descendants())
                .enter().append("g")
                .attr("class", "node")
                .attr("transform", d => `translate(${d.y},${d.x})`);
            
            node.append("circle")
                .attr("r", 10)
                .on("click", function(event, d) {
                    showTooltip(event, d);
                });
            
            node.append("text")
                .attr("dy", ".35em")
                .attr("x", d => d.children ? -13 : 13)
                .style("text-anchor", d => d.children ? "end" : "start")
                .text(d => d.data.name);
            
            function showTooltip(event, d) {
                const tooltip = d3.select(".tooltip");
                tooltip.style("display", "block")
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px")
                    .html(`
                        <h3>${d.data.name}</h3>
                        <p>${d.data.description || ""}</p>
                    `);
            }
            
            function askQuestion() {
                const question = document.getElementById("question").value;
                // Send question to backend
                window.parent.postMessage({
                    type: "askQuestion",
                    question: question
                }, "*");
            }
            
            // Close tooltip when clicking elsewhere
            document.addEventListener("click", function(event) {
                if (!event.target.closest(".node")) {
                    d3.select(".tooltip").style("display", "none");
                }
            });
        </script>
    </body>
    </html>
    """


def generate_enhanced_diagram(learning_plan):
    """Generate a detailed diagram based on the learning plan"""
    try:
        # Convert learning plan to D3 format with error handling
        d3_data = {"name": "Learning Plan", "children": []}

        # Split learning plan into sections
        sections = learning_plan.split("\n\n")

        # Process each section
        current_section = None
        for section in sections:
            if section.strip():
                if ":" in section:
                    title, content = section.split(":", 1)
                    section_data = {
                        "name": title.strip(),
                        "description": content.strip(),
                        "children": [],
                    }
                    d3_data["children"].append(section_data)
                    current_section = section_data
                elif current_section:
                    # Add as subsection to current section
                    current_section["children"].append(
                        {"name": section.strip(), "description": ""}
                    )

        # Create the interactive HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                .node circle {{
                    fill: white;
                    stroke: #4CAF50;
                    stroke-width: 2px;
                }}
                .node text {{
                    font: 12px sans-serif;
                }}
                .link {{
                    fill: none;
                    stroke: #ccc;
                    stroke-width: 1px;
                }}
                .tooltip {{
                    position: absolute;
                    background: white;
                    border: 1px solid #ddd;
                    padding: 10px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }}
            </style>
        </head>
        <body>
            <div id="diagram"></div>
            <script>
                const data = {json.dumps(d3_data)};
                
                const width = 800;
                const height = 600;
                const margin = {{top: 20, right: 90, bottom: 30, left: 90}};
                
                const tree = d3.tree()
                    .size([height - margin.top - margin.bottom, width - margin.left - margin.right]);
                
                const svg = d3.select("#diagram")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .append("g")
                    .attr("transform", `translate(${{margin.left}},${{margin.top}})`);
                
                const root = d3.hierarchy(data);
                const nodes = tree(root);
                
                const link = svg.selectAll(".link")
                    .data(nodes.links())
                    .enter()
                    .append("path")
                    .attr("class", "link")
                    .attr("d", d3.linkHorizontal()
                        .x(d => d.y)
                        .y(d => d.x));
                
                const node = svg.selectAll(".node")
                    .data(nodes.descendants())
                    .enter()
                    .append("g")
                    .attr("class", d => "node" + (d.children ? " node--internal" : " node--leaf"))
                    .attr("transform", d => `translate(${{d.y}},${{d.x}})`);
                
                node.append("circle")
                    .attr("r", 7);
                
                node.append("text")
                    .attr("dy", ".35em")
                    .attr("x", d => d.children ? -13 : 13)
                    .style("text-anchor", d => d.children ? "end" : "start")
                    .text(d => d.data.name);
                
                // Add tooltips
                const tooltip = d3.select("body")
                    .append("div")
                    .attr("class", "tooltip")
                    .style("opacity", 0);
                
                node.on("mouseover", function(event, d) {{
                    tooltip.transition()
                        .duration(200)
                        .style("opacity", .9);
                    tooltip.html(d.data.description || d.data.name)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", function(d) {{
                    tooltip.transition()
                        .duration(500)
                        .style("opacity", 0);
                }});
            </script>
        </body>
        </html>
        """

        return html_content

    except Exception as e:
        # Return a simple error diagram
        return f"""
        <svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="700" height="500" fill="#fee" stroke="#f00"/>
            <text x="400" y="300" text-anchor="middle" font-size="20" fill="#700">
                Error Generating Diagram: {str(e)}
            </text>
        </svg>
        """


def validate_diagram(content):
    """Validate the diagram content"""
    if not content:
        return False
    if not isinstance(content, str):
        return False
    if "<!DOCTYPE html>" not in content:
        return False
    if "<svg" not in content:
        return False
    return True


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

    try:
        # Generate and display the diagram
        diagram_html = generate_enhanced_diagram(st.session_state.learning_plan)
        components.html(diagram_html, height=700)

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

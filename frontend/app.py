import streamlit as st
import os
from openai import OpenAI

# Set up the OpenAI client
client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )  # Set your OpenAI API key in environment
)

# Streamlit app frontend
st.title("📊 Diagram Generator")
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
                "content": "You are a diagram generation assistant. Generate diagrams in SVG format. Always start your response with <svg and end with </svg>. Keep diagrams simple and clear.",
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
            # Create two columns for layout
            col1, col2 = st.columns([3, 1])

            with col1:
                # Display the SVG
                st.write("### Generated Diagram:")
                st.components.v1.html(svg_content, height=400)

            with col2:
                # Download button
                st.download_button(
                    label="💾 Download SVG",
                    data=svg_content,
                    file_name="diagram.svg",
                    mime="image/svg+xml",
                )

                # View source button
                if st.button("🔍 View SVG Source"):
                    st.code(svg_content, language="xml")

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
    for i, item in enumerate(
        st.session_state.history[-5:]
    ):  # Show last 5 diagrams
        if st.button(f"Diagram {len(st.session_state.history)-i}"):
            st.components.v1.html(item["svg"], height=300)

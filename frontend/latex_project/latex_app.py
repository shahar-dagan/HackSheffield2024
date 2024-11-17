import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import tempfile
import subprocess
import base64
import io
import openai
import json
import os
from dotenv import load_dotenv

# Use relative path for loading files
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load model prompt
with open(os.path.join(current_dir, "model_prompt.txt"), "r") as file:
    prompt = file.read()

with open(os.path.join(current_dir, "start_boiler_plate.txt"), "r") as file:
    start_boiler_plate = file.read()

# Load environment variables
load_dotenv()

# Get OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found in environment variables")
    st.stop()

client = openai.OpenAI(api_key=api_key)


def convert_image_to_latex_code(image_data, image_type):
    MAKE_REQUEST = True

    if MAKE_REQUEST:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_type};base64,{image_data}"
                                },
                            }
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=1024,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            response_data = response.to_dict()
        except Exception as e:
            st.error(f"Error calling OpenAI API: {str(e)}")
            return None

        with open("4omini_json_response_data.json", "w") as file:
            json.dump(response_data, file, indent=4)
    else:
        with open("4omini_json_response_data.json", "r") as file:
            response_data = json.loads(file.read())

    latex = response_data["choices"][0]["message"]["content"]

    start_token = "\\begin{align}"
    end_token = "\\end{align}"

    start = latex.find(start_token)
    end = latex.find(end_token) + len(end_token)

    latex = latex[start:end]

    end_boiler_plate = "\n\end{document}"
    # end_boiler_plate = ""

    latex = start_boiler_plate + latex + end_boiler_plate

    with open("4omini_produced_latex.tex", "w") as file:
        file.write(latex)

    print("latex saved in file")
    # print(latex)

    return latex


def generate_pdf(latex_text):
    # create temp latex file
    with open("temp_file.tex", "w") as file:
        file.write(latex_text)

    result = subprocess.run(
        ["pdflatex", "temp_file.tex"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # print(result)

    # assert result.returncode != 0

    # read and delete pdf file
    with open("temp_file.pdf", "rb") as pdf_file:
        pdf_data = pdf_file.read()

    # subprocess.run(['rm', "temp_file.tex", "temp_file.pdf", "temp_file.log", "temp_file.aux"])

    return pdf_data

    # create file of pdf of this latex locally


def run_latex_app():
    """Main function to run the LaTeX converter app"""
    st.title("Math Image to LaTeX PDF Converter")
    st.markdown(
        "Upload an image containing mathematical expressions, and we'll convert it to a downloadable PDF."
    )

    uploaded_image_data = st.file_uploader(
        "Upload an Image", type=["png", "jpg", "jpeg"]
    )

    if uploaded_image_data:
        # Step 2: Display the uploaded image
        file_format = uploaded_image_data.type.split("/")[1].upper()

        uploaded_image = Image.open(uploaded_image_data)

        desired_resolution = (512, 512)
        uploaded_image = uploaded_image.resize(desired_resolution)

        st.image(
            uploaded_image, caption="Uploaded Image", use_column_width=True
        )

        buffer = io.BytesIO()
        uploaded_image.save(
            buffer, format=file_format
        )  # Dynamically use the format based on the uploaded file type
        buffer.seek(0)

        # image_bytes = uploaded_image.decode('utf-8')
        # image_bytes = base64.b64decode(uploaded_image)
        encoded_image = base64.b64encode(buffer.read()).decode("utf-8")

        latex_code = convert_image_to_latex_code(
            encoded_image, file_format.lower()
        )

        st.text_area("Extracted LaTeX Code", latex_code)

        # Step 4: Convert LaTeX to PDF
        pdf_data = generate_pdf(latex_code)

        # Step 5: Provide download link
        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name="output.pdf",
            mime="application/pdf",
        )


if __name__ == "__main__":
    run_latex_app()

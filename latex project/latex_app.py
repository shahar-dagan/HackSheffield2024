import streamlit as st
from PIL import Image
import requests
from io import BytesIO
from pylatex import Document, NoEscape
# from pylatex.utils import escape_latex
import tempfile
import subprocess



def convert_image_to_latex_code(image_data):
    with open("sample.tex", "r") as file:
        return file.read()



def generate_pdf(latex_text):
    # create temp latex file
    with open("temp_file.tex", "w") as file:
        file.write(latex_text)


    result = subprocess.run(
        ['pdflatex', "temp_file.tex"], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # print(result)

    # assert result.returncode != 0

    
    # read and delete pdf file
    with open("temp_file.pdf", 'rb') as pdf_file:
        pdf_data = pdf_file.read()
    
    # subprocess.run(['rm', "temp_file.tex", "temp_file.pdf", "temp_file.log", "temp_file.aux"])

    return pdf_data


    # create file of pdf of this latex locally



# Step 1: Set up Streamlit interface
st.title("Math Image to LaTeX PDF Converter")
st.markdown("Upload an image containing mathematical expressions, and we'll convert it to a downloadable PDF.")

uploaded_image_data = st.file_uploader("Upload an Image", type=["png", "jpg", "jpeg"])

if uploaded_image_data:
    # Step 2: Display the uploaded image
    uploaded_image = Image.open(uploaded_image_data)
    st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)

    # # Step 3: Extract math as LaTeX using Mathpix (requires Mathpix API credentials)
    # image_data = {
    #     "src": f"data:image/jpeg;base64,{uploaded_image.getvalue().decode('utf-8')}",
    #     "formats": ["text", "latex"],
    #     "ocr": ["math"],
    # }

    latex_code = convert_image_to_latex_code(uploaded_image)

    st.text_area("Extracted LaTeX Code", latex_code)

    # Step 4: Convert LaTeX to PDF
    pdf_data = generate_pdf(latex_code)

    # Step 5: Provide download link
    st.download_button(
        label="Download PDF",
        data=pdf_data,
        file_name="output.pdf",
        mime="application/pdf"
    )

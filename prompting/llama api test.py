import requests


with open("hugging_face_api_key.key", "r") as file:
    hugging_face_key = file.read()


# daydreamer
# model = "Llama-3.2-8B"

model= "Meta-Llama-3-8B-Instruct"
# model= "Meta-Llama-3-70B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/meta-llama/{model}"


headers = {"Authorization": f"Bearer {hugging_face_key}"}

def query(payload):
	response = requests.post(API_URL, headers=headers, json=payload)
	# response.raise_for_status()
	return response.json()

end_token = "</svg>\n```"
# end_token = "</svg>"
prompt = "Make SVG code for a diagram of a neural network. (Respond only with plain SVG code with no additional formatting)"
output = query({
	"inputs": prompt,
	"parameters": {
        "max_new_tokens": 1000,
		"temperature": 1,
		"stop": [end_token]
    }
})


print(output)


text = output[0]["generated_text"]

# remove_prompt
text = text[len(prompt):]

start = text.find("<svg")
end = text.find("<\svg") -3

text = text[start:end]

with open("lama diagram.svg", "w") as file:
	file.write(text)

print(text)
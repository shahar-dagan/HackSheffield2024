from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "You are a helpful explainer and diagram creator. You will receive instructions to create a diagram to help explain topic. Your diagram should be infomative. You will privide it as SVD code. You will only respond with raw SVD code without formatting. "
        }
      ]
    }
  ],
  temperature=1,
  max_tokens=1025,
  top_p=1,
  frequency_penalty=0,
  presence_penalty=0,
  response_format={
    "type": "text"
  },
  stop=["<<<explanation_end>>>"]
)
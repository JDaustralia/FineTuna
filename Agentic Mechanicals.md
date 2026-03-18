# Reading .md files into local LLM’s

## In vLLM use the following script:

with open("notes.md", "r") as f:
    content = f.read()

resp = client.chat.completions.create(
    model="mistral-small-4-nvfp4",
    messages=[
        {"role": "user", "content": f"Here is the file:\n\n{content}"}
    ]
)


## In Ollama, use the following script

{
  "model": "llama3",
  "messages": [
    {"role": "user", "content": "Here is the file:\n\n" + contents_of_file }
  ]
}

## In llama.cpp, use the following command

/read path/to/file.md


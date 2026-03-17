# Fine tuning 101

As background running the process involves:

Step 1 – running a python scipt (called FineTune-xxxx.py) that uses LoRA Adapters from FastLanguageModel and SFTTrainer  to train data from a selected .JSONL dataset.  There are several LoRA and SFTTrainer parameters that affect the efficacy of the training.  These are discussed separately.  This process uses an existing local LLM in .safetensor format as a base model.  The output of this script is adaptor_model.safetensors which is retained in a WSL subdirectory Project_Name/ftune_output

Step 2 – solidify_safetensors_nogpu.py (stored in Project_Name/scripts) is then used to merge the adaptor_model.safetensors with the base model .safetensors.  The output of this script is a .safetensors directory (including config.json, tokenizer.json and other necessary miscellaneous required files) called Project_Name/final_merged_model.   If the user intend to run the fine-tuned LLM in from .safetensors that can be done at this point. If the user wishes to run the LLM from gguf format, Step 3 will be necessary to convert the safetensors to gguf.

Step 3 – gguf_maker.py (stored in Project_Name/scripts) generates a single .gguf file that is stored in Project_Name/final_gguf_16bit_gguf    This .gguf file can be moved to an appropriate directory for long term use.  If running this gguf in Ollama you will need to ensure an appropriate Modelfile is linked to the gguf.

See the section ‘File source and name changes when rerunning’ for specific details on how to run and rerun these scripts.



## File source and name changes when rerunning

Move dataset.jsonl file to /home/Project_Name /data_prepared/
	Make sure new file has a unique name
	Change source file name in FineTune-xxx.py to match

Running FineTune-xxx.py will create output in /home/Project_Name /ftune_output/
	Remove or rename old content in that file before rerunning

Solid_safetensors_nogpu.py runs automatically after this.  It will need 
	/home/Project_Name /final_merged_model to be cleared

gguf_maker.py runs automatically after this. It will need
	/home/Project_Name /final_16bit and 
	/home/Project_Name /final_16bit_gguf to be cleared

To run FineTune-xxx.py  you need to open Ubuntu and run the following:
	Source ~/ai_env/bin/activate
	cd Compliance/scripts
	python3 FineTune-xxx.py

The .gguf file found in 	/home/Project_Name /final_16bit_gguf  will need to be move to D:\LLM\gguf\model_name\

You are now ready to proceed to the "Running gguf's in Ollama" section.


## Running gguf’s in Ollama

Step 1 - move the relevant .gguf file to D:\LLM\gguf\model_name\

Step 2 – Create a model file. This will be saved at D:\LLM\modelfiles\model_name  For example the syntax below is used for yes/no compliance classification:

FROM "D:\LLM\gguf\model_name\final_merged_model.F16.gguf"

TEMPLATE """
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
{{ .Prompt }}
<|start_header_id|>assistant<|end_header_id|>
"""

SYSTEM """You output only 'yes' or 'no'. No explanations."""

PARAMETER temperature 0
PARAMETER num_ctx 16384
PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"

Step 3  - from the D:\LLM\modelfiles\model_name directory you need to run the following:  
ollama create model_short_name -f Modelfile

Step 3 – the model will be available in python.  The following is an example of a python function that is used as a yes/no classifier:  

def classify_with_llama(text):
    """Classify email using your fine tuned Llama3 model via Ollama."""

    # IMPORTANT: send ONLY the email text.
    # The Modelfile system prompt handles the instruction.
    prompt = text.strip()

    try:
        response = ollama_client.generate(
            model=" model_short_name
            prompt=prompt
        )
        answer = response['response'].strip().lower()

        # Be strict: only accept exact "yes"
        result = answer == "yes"

        return result, answer, ""

    except Exception as e:
        return False, "", str(e)

## Setting Fine Tuning Parameters:

Bang for buck order of model impact:

1 – Us a well balanced and defined dataset

2 -  Epochs – more epochs, more overfitting risk, but too low and there is an underfitting risk.

3 – rank and alpha (actually start with just adjusting alpha first)
- Effects:
  - Lower r → smaller adapter, less capacity, more “surgical” changes
  - Higher r → more capacity to model subtle patterns, more risk of overfitting/forgetting

In other words, decrease rank if there's overfitting and increase rank if it’s underfitting the dataset.
Note: Rank – safe range:  16 – 64

Aplha
	Effective strength is alpha/rank

Alpha = same as Rank -> Gentle
Alpha = 2x Rank -> Strong
Alpha = 3x Rank -> Very strong


Note

Effective Batch size= per_device_train_batch_size x gradient_accumulation_steps 
Eg 8 x 4 = 32.  


SFTTraining Parameters:

Set the learning rate between 1e-4 and 2e-4 using the following:
def compute_learning_rate(value,
                          factor=5.45454545454545e-08,
                          decimals=5,
                          min_lr=1e-4,
                          max_lr=2e-4):
    """
    Mirrors: =ROUND(value * 5.45454545454545E-08, 5) using Python's bankers rounding,
    then clamps to [min_lr, max_lr].
    """
    raw = value * factor
    rounded = round(raw, decimals)  # bankers rounding
    # clamp
    if rounded < min_lr:
        return min_lr
    if rounded > max_lr:
        return max_lr
    return rounded




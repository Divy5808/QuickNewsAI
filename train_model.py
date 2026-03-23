import os
import torch
import pandas as pd
from transformers import (
    AutoTokenizer, 
    AutoModelForSeq2SeqLM, 
    Seq2SeqTrainingArguments, 
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from datasets import Dataset

# 1. Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "training_data.csv")
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "qnai_model")

# 2. Check if data exists and has enough rows
if not os.path.exists(DATA_PATH):
    print(f"❌ Error: Data file not found at {DATA_PATH}")
    exit(1)

df = pd.read_csv(DATA_PATH)
if len(df) < 10:
    print("⚠️ WARNING: Your data.csv currently has very few rows!")
    print("To train a model properly so it doesn't give garbage output, you need at least 500-1000 properly formatted news articles and their summaries.")
    print("Format should be: text,summary (header row included)")

# 3. Load Datasets
dataset = Dataset.from_pandas(df)

# 4. Load Base Model and Tokenizer (Start with a good base model instead of a broken one)
BASE_MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
print(f"Loading Base Model: {BASE_MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_NAME)

# 5. Preprocessing the data
def preprocess_function(examples):
    inputs = [doc for doc in examples["text"]]
    # The tokenizer handles adding special tokens and padding
    model_inputs = tokenizer(inputs, max_length=1024, truncation=True)
    
    # Setup targets for summarization
    labels = tokenizer(text_target=examples["summary"], max_length=150, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

print("Tokenizing data...")
tokenized_datasets = dataset.map(preprocess_function, batched=True)

# 6. Setup Training configurations
training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    learning_rate=2e-5,
    per_device_train_batch_size=2,
    weight_decay=0.01,
    save_total_limit=2,
    num_train_epochs=3,      # Increase epochs if you have small data, but avoid overfitting
    predict_with_generate=True,
    logging_steps=10,
    save_strategy="epoch",
)

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

# 7. Setup Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets,
    processing_class=tokenizer,
    data_collator=data_collator,
)

# 8. Train!
print("🚀 Starting training... This will take some time depending on your data size and whether you are using a GPU.")
trainer.train()

# 9. Save the Final Model properly
print(f"✅ Training complete. Saving the new model to {MODEL_OUTPUT_DIR}...")
model.save_pretrained(MODEL_OUTPUT_DIR)
tokenizer.save_pretrained(MODEL_OUTPUT_DIR)
print("🎉 Model successfully saved! You can now use your newly trained 'qnai_model'.")


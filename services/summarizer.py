# ==========================================
# 🔥 LIGHT + RELIABLE SUMMARIZER (NO PIPELINE ERRORS)
# ==========================================

import os
# No top-level heavy imports to keep startup ultra-fast
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Using the newly trained local qnai_model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_MODEL = os.path.join(BASE_DIR, "qnai_model")

# 🔥 Update to use the user's own cloud model if local model isn't found
if os.path.exists(LOCAL_MODEL) and os.path.exists(os.path.join(LOCAL_MODEL, "config.json")):
    MODEL_NAME = LOCAL_MODEL
else:
    MODEL_NAME = "Dev5808/QuickNewsAI-Model"

# Global model/tokenizer (Lazy Loading)
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    if tokenizer is not None and model is not None:
        return tokenizer, model
        
    print(f"Loading Summarizer Model: {MODEL_NAME}...")
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    except Exception as e:
        print(f"❌ CRITICAL MODEL LOAD ERROR: {e}")
        raise e
        
    return tokenizer, model

def summarize_text(text, summary_length=150):
    t_obj, m_obj = load_model()
    
    if not text or len(text.strip()) < 200:
        return "Summary not available."

    text = text.replace("\n", " ").strip()

    # Adjust length based on slider
    if summary_length <= 100:        # SHORT
        text = text[:1500]           # increased from 800
        max_len = 65
        min_len = 30

    elif summary_length >= 200:      # LONG
        text = text[:4000]           # increased from 2500
        max_len = 250
        min_len = 100

    else:                            # MEDIUM
        text = text[:2800]           # increased from 1500
        max_len = 160
        min_len = 60

    try:
        inputs = t_obj(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        )

        input_length = inputs["input_ids"].shape[1]
        
        # Dynamically scale lengths to prevent the model from generating more tokens than the input length
        actual_min_len = min(min_len, max(10, input_length // 3))
        actual_max_len = min(max_len, max(20, int(input_length * 0.8)))

        output_ids = m_obj.generate(
            **inputs,
            max_length=actual_max_len,
            min_length=actual_min_len,
            num_beams=4,
            no_repeat_ngram_size=3,
            length_penalty=2.0,
            early_stopping=True
        )

        summary = t_obj.decode(output_ids[0], skip_special_tokens=True).strip()

        # 🔥 HEAL: Check for model hallucination / gibberish (common in T5/BART failures)
        # If output is too short, or has weird characters/tokens, or is highly repetitive
        bad_patterns = ["(i: )", "(फ ):", "Answer:", "Yes for yes", "no for no"]
        is_bad = any(p in summary for p in bad_patterns) or len(summary) < 20
        
        # Extractive Fallback if model failed but input exists
        if is_bad and len(text) > 200:
            print("SUMMARIZER FALLBACK: Model failed to generate valid news.")
            # Simple extractive fallback: first 2-3 sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) >= 2:
                summary = " ".join(sentences[:2])
                if len(summary) < summary_length // 2:
                    summary = " ".join(sentences[:3])
            else:
                summary = text[:250] + "..."

        return summary.replace("\n", " ").strip()

    except Exception as e:
        print("SUMMARY ERROR:", e)
        return text[:300] + "..."

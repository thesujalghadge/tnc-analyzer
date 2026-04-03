# -------------------------------
# IMPORTS
# -------------------------------
import base64
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os
from dotenv import load_dotenv

# -------------------------------
# CONFIG
# -------------------------------
load_dotenv()

USE_GEMINI = True   # 🔥 Now you can use Gemini safely

# -------------------------------
# LOAD LOCAL MODEL
# -------------------------------
print("🔄 Loading FLAN-T5 model...")

tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small")

print("✅ Local model ready")

# -------------------------------
# GEMINI SETUP
# -------------------------------
if USE_GEMINI:
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("No API key found")

        genai.configure(api_key=api_key)

        # 🔥 Using 2.5 (your working model)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")

        print("✅ Gemini ready")

    except Exception as e:
        print("❌ Gemini failed, fallback to local:", e)
        USE_GEMINI = False


# =========================================================
# 🔹 LOCAL FUNCTIONS (FALLBACK)
# =========================================================

def local_summary(chunks):
    key_points = []

    for chunk in chunks[:3]:
        chunk = chunk[:800]

        prompt = f"What is the main point?\n{chunk}"

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

        outputs = model.generate(
            **inputs,
            max_length=25,
            num_beams=4
        )

        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)

        if len(summary) > 10:
            key_points.append(summary)

    return "\n".join([f"• {s}" for s in key_points])


def local_explain(reason):
    prompt = f"Explain this risk simply:\n{reason}"

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

    outputs = model.generate(
        **inputs,
        max_length=20,
        num_beams=4
    )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if len(result) < 5:
        return reason

    return result


# =========================================================
# 🔹 GEMINI FUNCTIONS (POLISHED)
# =========================================================

def gemini_summary(chunks):
    try:
        text = " ".join(chunks[:3])[:1500]

        prompt = f"""
Summarize this Terms and Conditions.

Rules:
- Use ONLY bullet points
- No headings
- Keep it simple
- Max 5 points

{text}
"""

        response = gemini_model.generate_content(prompt)

        if hasattr(response, "text") and response.text:
            return response.text.strip()

    except Exception as e:
        print("❌ Gemini Summary Error:", e)

    return None


def gemini_explain(reason):
    try:
        prompt = f"""
Explain this risk clearly for a user.

Risk: {reason}

Rules:
- Be specific
- Mention what can happen
- Max 12 words
"""

        response = gemini_model.generate_content(prompt)

        if hasattr(response, "text") and response.text:
            return response.text.strip()

    except Exception as e:
        print("❌ Gemini Explain Error:", e)

    return None




# =========================================================
# 🔹 PUBLIC FUNCTIONS (SMART SWITCH)
# =========================================================

def generate_summary(chunks):
    if USE_GEMINI:
        result = gemini_summary(chunks)
        if result:
            return result

    return local_summary(chunks)


def explain_simple(clause, reason=None, category=None):
    if USE_GEMINI:
        result = gemini_explain(reason)
        if result:
            return result

    return local_explain(reason)


def extract_text_from_images(image_payloads):
    if not USE_GEMINI:
        raise ValueError("Image analysis currently requires Gemini to extract text from document photos.")

    try:
        prompt = """
Extract the readable document text from these images.

Rules:
- Preserve the order of the pages/images
- Focus on the document text only
- Return plain text only
- Separate each page with a heading like [Page 1]
"""

        parts = [prompt]
        for image in image_payloads:
            parts.append({
                "mime_type": image["mime_type"],
                "data": base64.b64decode(image["data"]),
            })

        response = gemini_model.generate_content(parts)

        if hasattr(response, "text") and response.text:
            return response.text.strip()

    except Exception as e:
        print("❌ Gemini Image OCR Error:", e)

    raise ValueError("Could not extract text from the uploaded images.")

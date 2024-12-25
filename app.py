from flask import Flask, request, jsonify
from transformers import pipeline
import spacy
import os
import PyPDF2

# Temporary upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# Utility function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if not reader.pages:  # Check if there are any pages
                return ""  # Return empty string for empty PDF
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""  # Handle pages with no text
            return text
    except PyPDF2.errors.EmptyFileError:
        return ""  # Handle corrupted or unreadable PDFs

# Utility function to merge consecutive entities (unchanged)
def merge_consecutive_entities(entities):
    """
    Merges consecutive Hugging Face entities with a difference <= 1 between the end of one
    and the start of the next. Also removes unnecessary hashes from text.
    """
    # Sort entities based on the start position
    if len(entities) == 0:
        return []
    
    entities = sorted(entities, key=lambda x: x['start'])
    merged_entities = []
    current_entity = entities[0]  # Start with the first entity
    for i in range(1, len(entities)):
        next_entity = entities[i]
        
        # Check if the entities are consecutive
        if abs(current_entity['end'] - next_entity['start']) <= 1:
            if current_entity['end'] == next_entity['start']:
                current_entity['text'] += next_entity['text'].strip().replace("#", "")
            else:
                # Merge the entities
                current_entity['text'] += " " + next_entity['text'].strip().replace("#", "")
            current_entity['end'] = next_entity['end']
        else:
            # Finalize the current entity
            merged_entities.append(current_entity)
            current_entity = next_entity

    merged_entities.append(current_entity)
    return merged_entities

# Initialize Flask app
app = Flask(__name__)

# Load spaCy and Hugging Face NER models
nlp_spacy = spacy.load("en_core_web_sm")
nlp_huggingface = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Entity Extraction
def extract_spacy_entities(text):
    spacy_doc = nlp_spacy(text)
    entities = []
    for ent in spacy_doc.ents:
        entities.append({
            "start": ent.start,  # Token index of the first token in the entity
            "end": ent.end - 1,  # Token index of the last token in the entity
            "label": ent.label_,  # Entity label
            "text": ent.text      # Entity text
        })
    return entities

def extract_huggingface_entities(text):
    huggingface_entities_raw = nlp_huggingface(text)
    return [
        {"start": entity["start"], "end": entity["end"], "label": entity["entity"], "text": entity["word"], "score": float(entity["score"])}
        for entity in huggingface_entities_raw
    ]

# Scoring and Feedback System
def calculate_score(job_description, resume):
    # Extract Hugging Face entities and merge them
    job_hf_entities = extract_huggingface_entities(job_description) or []
    job_hf_entities_merged = merge_consecutive_entities(job_hf_entities) if job_hf_entities else []
    resume_hf_entities = extract_huggingface_entities(resume) or []
    resume_hf_entities_merged = merge_consecutive_entities(resume_hf_entities) if resume_hf_entities else []
    
    # Extract spaCy entities separately
    job_spacy_entities = extract_spacy_entities(job_description) or []
    resume_spacy_entities = extract_spacy_entities(resume) or []
    
    # Combine entity text into sets (lowercased for matching)
    job_entity_texts = set([ent["text"].lower() for ent in job_hf_entities_merged] +
                           [ent["text"].lower() for ent in job_spacy_entities])
    resume_entity_texts = set([ent["text"].lower() for ent in resume_hf_entities_merged] +
                              [ent["text"].lower() for ent in resume_spacy_entities])
    
    if not job_entity_texts:
        return 0

    # Calculate exact matches
    matched_entities = job_entity_texts.intersection(resume_entity_texts)
    score = len(matched_entities) * 2  # 2 points per exact match
    
    # Calculate partial matches (e.g., substrings)
    partial_matches = sum([1 for job_entity in job_entity_texts 
                           if any(resume_entity in job_entity for resume_entity in resume_entity_texts)])
    score += partial_matches
    
    # Penalize for missing entities from job description
    missing_entities = len(job_entity_texts - resume_entity_texts)
    score -= missing_entities  # -1 for each missing entity

    return score

@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    """
    Handle PDF upload for resume and process the job description in text.
    """
    # Get the uploaded PDF file
    file = request.files.get('resume')  # 'resume' is the key for the uploaded file
    job_description = request.form.get("job_description", "")
    
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed."}), 400

    # Save the uploaded PDF file temporarily
    pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(pdf_path)
    
    # Extract text from the uploaded PDF
    resume_text = extract_text_from_pdf(pdf_path)
    
    # Calculate score based on the extracted resume text and job description
    score = calculate_score(job_description, resume_text)
    
    return jsonify({
        "score": score,
        "resume_text": resume_text,
        "job_description": job_description
    })

# Flask Routes
@app.route("/parse-job", methods=["POST"])
def parse_job():
    """
    Extracts entities from a job description using Hugging Face and spaCy.
    """
    job_description = request.json.get("description", "")
    
    # Extract entities
    spacy_entities = extract_spacy_entities(job_description)
    huggingface_entities_raw = extract_huggingface_entities(job_description)
    huggingface_entities_merged = merge_consecutive_entities(huggingface_entities_raw)
    
    return jsonify({
        "spacy_entities": spacy_entities,
        "huggingface_entities": huggingface_entities_merged
    })

@app.route("/score-job", methods=["POST"])
def score_job():
    job_description = request.json.get("job_description", "")
    resume = request.json.get("resume", "")
    
    # Calculate score based on entity matches
    score = calculate_score(job_description, resume)
    
    return jsonify({"score": score})

@app.route("/feedback", methods=["POST"])
def get_feedback():
    """
    Generates feedback by identifying missing and partially matched entities in the resume.
    """
    job_description = request.json.get("job_description", "")
    resume = request.json.get("resume", "")
    
    # Extract entities from job description and resume
    job_entities = extract_huggingface_entities(job_description) + extract_spacy_entities(job_description)
    resume_entities = extract_huggingface_entities(resume) + extract_spacy_entities(resume)

    # Merge consecutive entities for both job description and resume
    job_entities = merge_consecutive_entities(job_entities)
    resume_entities = merge_consecutive_entities(resume_entities)

    # Compare entities based on their text
    job_texts = set([ent["text"].lower() for ent in job_entities])
    resume_texts = set([ent["text"].lower() for ent in resume_entities])

    # Identify missing entities in the resume (those in job description but not in resume)
    missing_entities = list(job_texts - resume_texts)
    
    # Identify partially matched entities (those that contain substrings from the resume)
    partial_matches = [job for job in job_texts if any(res in job for res in resume_texts)]

    # Return the feedback as a JSON response
    return jsonify({
        "missing_entities": missing_entities,
        "partial_matches": partial_matches
    })

if __name__ == "__main__":
    app.run(debug=True)

import pytest
from app import app, calculate_score, extract_spacy_entities, extract_huggingface_entities, extract_text_from_pdf, merge_consecutive_entities

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test for the entity extraction function
def test_extract_spacy_entities():
    text = "Alice is a software engineer at OpenAI."
    entities = extract_spacy_entities(text)
    assert len(entities) > 0
    assert any(ent['label'] == "ORG" for ent in entities)

def test_extract_huggingface_entities():
    text = "Alice is a software engineer at OpenAI."
    entities = extract_huggingface_entities(text)
    assert len(entities) > 0
    assert any(ent['label'] == "I-ORG" for ent in entities)

# Test for the scoring function
def test_calculate_score():
    job_description = "Looking for a software engineer with Python experience."
    resume = "I am a software engineer skilled in Python and JavaScript."
    score = calculate_score(job_description, resume)
    assert score > 0  # Ensure the score is positive for matching skills

# Test the /parse-job endpoint
def test_parse_job(client):
    job_description = {"description": "Python developer with experience in Flask and SQL"}
    response = client.post('/parse-job', json=job_description)
    assert response.status_code == 200
    data = response.get_json()
    assert "spacy_entities" in data
    assert "huggingface_entities" in data


def test_missing_file(client):
    response = client.post("/upload-resume", data={"job_description": "Sample job description"})
    assert response.status_code == 400
    assert response.json["error"] == "No file uploaded"

def test_empty_pdf():
    with open("empty.pdf", "wb") as f:
        f.write(b"")  # Create an empty PDF
    text = extract_text_from_pdf("empty.pdf")
    assert text == ""  # Ensure no text is extracted

def test_merge_single_entity():
    entities = [{"start": 0, "end": 4, "text": "test", "label": "LABEL"}]
    result = merge_consecutive_entities(entities)
    assert result == entities

def test_merge_overlapping_entities():
    entities = [
        {"start": 0, "end": 4, "text": "test", "label": "LABEL"},
        {"start": 3, "end": 8, "text": "testing", "label": "LABEL"}
    ]
    result = merge_consecutive_entities(entities)
    assert result == [{"start": 0, "end": 8, "text": "test testing", "label": "LABEL"}]

def test_calculate_score_no_matches():
    job_description = "This job requires Python and machine learning skills."
    resume = "This candidate has Java and web development experience."
    score = calculate_score(job_description, resume)
    assert score == 0  # No matches, score should be 0

def test_calculate_score_partial_matches():
    job_description = "Looking for Python developers with deep learning expertise."
    resume = "Proficient in Python, familiar with deep learning frameworks."
    score = calculate_score(job_description, resume)
    assert score > 0  # Partial matches should result in a positive score

def test_calculate_score_no_keywords():
    job_description = ""
    resume = ""
    score = calculate_score(job_description, resume)
    assert score == 0  # No keywords in either text, score should be 0


def test_upload_resume_success(client):
    # Create a mock PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    data = {
        "resume": (pdf_content, "resume.pdf"),
        "job_description": "Data Scientist role requiring Python and ML experience"
    }
    response = client.post("/upload-resume", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert "score" in response.json

def test_parse_job_empty_description(client):
    response = client.post("/parse-job", json={"description": ""})
    assert response.status_code == 200
    assert response.json["spacy_entities"] == []
    assert response.json["huggingface_entities"] == []
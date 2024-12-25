# Project Description

This project aims to simulate a scoring mechanism for resumes in accordance with the job descriptions they are submitted for. The basic idea is simple: parse keywords in both the resume and job description using NLP, then calculate a score based on matching and/or partially matching keywords.

- app.py contains 3 endpoints for parsing a job description, uploading a resume, and getting feedback on matching/partially matching words. PDF resume uploads are supported as well through PyPDF2.
- test_app.py contains unit tests for testing functionality of the endpoints.
- api_test.py contains a sample test for measuring the time taken for an API response.

The backbone of this project is the use of spacy, a NLP library in Python, and Hugging Face Transformers. Combining both leads to the detection of more relevant keywords. 

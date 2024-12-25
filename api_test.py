import requests
import time

# Example file and job description
resume_file = 'C:\\Users\\rmur3\\Downloads\\Rathik_Murtinty_Resume (1).pdf'  # Provide the path to your resume file
job_description = "We are seeking a skilled software engineer with expertise in Python, Rust, AWS, Azure, and cryptography to join our innovative team. The ideal candidate will have experience building secure, scalable applications in the cloud and a deep understanding of cryptographic protocols. Responsibilities include developing backend services using Python and Rust, deploying applications on AWS and Azure, implementing cryptographic solutions, and optimizing cloud infrastructure. The candidate will also work with cross-functional teams to ensure high performance, security, and reliability of our cloud-based systems. Strong experience in AWS and Azure cloud services, along with a solid understanding of encryption techniques and secure communication protocols, is required. Knowledge of containerization and orchestration tools (eg, Docker, Kubernetes) is a plus."

url = 'http://127.0.0.1:5000/upload-resume'

# Open the file in binary mode
with open(resume_file, 'rb') as f:
    files = {'resume': f}
    data = {'job_description': job_description}
    
    # Measure the response time
    start_time = time.time()
    response = requests.post(url, files=files, data=data)
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"API response time: {response_time:.4f} seconds")
    print(f"API Response: {response.json()}")

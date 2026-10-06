"""Job-description reading and requirement extraction.

OWNER: Toluwalase Ayeoyenikan  (Job Description Processing)

Will turn a job description - typed by the user or uploaded as TXT/PDF/DOCX -
into a structured JobDescription object (skills, years of experience, education)
that the matcher and AI modules consume. Reuses document_reader to read files.
"""
"""
Job-description reading and requirement extraction.

OWNER: Toluwalase Ayeoyenikan (Job Description Processing)

This module:
    - Accepts a typed job description or a TXT/PDF/DOCX file
    - Extracts the job title
    - Extracts required skills
    - Extracts years of experience
    - Extracts education requirements
    - Stores the results in a structured JobDescription object

Reuses document_reader.py to read files.
"""

import re
from dataclasses import dataclass, field

# Reuse the existing document reader
from document_reader import read_document, clean_text


@dataclass
class JobDescription:
    """Stores information extracted from a job description."""

    title: str = ""
    skills: list[str] = field(default_factory=list)
    years_experience: int = 0
    education: list[str] = field(default_factory=list)


def read_job_description(text):
    """
    Clean a typed job description.

    Parameters:
        text (str): Job description entered by the user.

    Returns:
        str: Cleaned job description.
    """

    if not isinstance(text, str):
        raise TypeError("Job description must be text.")

    return clean_text(text)


def read_job_description_file(file_path):
    """
    Read a job description from a TXT, PDF or DOCX file.

    Uses document_reader.py.
    """

    text = read_document(file_path)

    return clean_text(text)


def extract_title(text):
    """Extract the job title from the job description."""

    patterns = [
        r"job\s*title\s*[:\-]\s*(.+)",
        r"position\s*[:\-]\s*(.+)",
        r"title\s*[:\-]\s*(.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            title = match.group(1).strip()

            # Stop at common section headings
            title = re.split(
                r"\b(requirements|responsibilities|qualifications|skills)\b",
                title,
                flags=re.IGNORECASE
            )[0]

            return title.strip(" .:-")

    return ""


def extract_years_experience(text):
    """Extract the minimum required years of experience."""

    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
        r"minimum\s*(?:of\s*)?(\d+)\s*years?",
        r"at\s*least\s*(\d+)\s*years?"
    ]

    years_found = []

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            years_found.append(int(match))

    if years_found:
        return max(years_found)

    return 0


def extract_skills(text):
    """
    Extract commonly requested skills.

    This list can be expanded as the CV Screener project grows.
    """

    possible_skills = [
        "Python",
        "Java",
        "JavaScript",
        "C++",
        "C#",
        "SQL",
        "HTML",
        "CSS",
        "React",
        "Node.js",
        "Django",
        "Flask",
        "Machine Learning",
        "Artificial Intelligence",
        "Data Analysis",
        "Data Science",
        "Excel",
        "Microsoft Excel",
        "Power BI",
        "Tableau",
        "Communication",
        "Leadership",
        "Teamwork",
        "Project Management",
        "Problem Solving",
        "Critical Thinking",
        "Figma",
        "UI/UX",
        "Git",
        "GitHub",
        "Microsoft Office",
        "Customer Service",
        "Research",
        "Marketing",
        "Sales"
    ]

    found_skills = []

    for skill in possible_skills:

        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)

    return found_skills


def extract_education(text):
    """Extract education requirements."""

    education_keywords = [
        "Bachelor's degree",
        "Bachelor degree",
        "Bachelor of Science",
        "Bachelor of Arts",
        "BSc",
        "B.Sc",
        "BA",
        "B.A",
        "Master's degree",
        "Master degree",
        "Master of Science",
        "Master of Arts",
        "MSc",
        "M.Sc",
        "MA",
        "M.A",
        "PhD",
        "Ph.D",
        "Doctorate",
        "Higher National Diploma",
        "HND",
        "National Diploma",
        "ND"
    ]

    found_education = []

    for education in education_keywords:

        if re.search(
            re.escape(education),
            text,
            re.IGNORECASE
        ):
            if education not in found_education:
                found_education.append(education)

    return found_education


def extract_requirements(text):
    """
    Extract all requirements from a job description.

    Returns:
        JobDescription object.
    """

    text = read_job_description(text)

    job = JobDescription()

    job.title = extract_title(text)
    job.skills = extract_skills(text)
    job.years_experience = extract_years_experience(text)
    job.education = extract_education(text)

    return job


def extract_requirements_from_file(file_path):
    """
    Read a job description file and extract its requirements.

    Supports:
        TXT
        PDF
        DOCX
    """

    text = read_job_description_file(file_path)

    return extract_requirements(text)


def display_job_description(job):
    """Display the extracted job description requirements."""

    print("\nJOB DESCRIPTION")
    print("=" * 40)

    print(
        "Job Title:",
        job.title if job.title else "Not specified"
    )

    print(
        "Years of Experience:",
        job.years_experience
        if job.years_experience > 0
        else "Not specified"
    )

    print("\nRequired Skills:")

    if job.skills:
        for skill in job.skills:
            print(f"- {skill}")
    else:
        print("- None found")

    print("\nEducation:")

    if job.education:
        for education in job.education:
            print(f"- {education}")
    else:
        print("- None found")


def main():
    """Run the Job Description Processing module."""

    print("CV Screener - Job Description Processor")
    print("=" * 45)

    print("\nHow would you like to provide the job description?")
    print("1. Type/paste the job description")
    print("2. Provide a TXT/PDF/DOCX file")

    choice = input("\nEnter 1 or 2: ").strip()

    try:

        if choice == "1":

            print("\nPaste the job description below.")
            print("Press Enter twice when you are finished.\n")

            lines = []

            while True:
                line = input()

                if line == "":
                    break

                lines.append(line)

            text = "\n".join(lines)

            job = extract_requirements(text)

        elif choice == "2":

            file_path = input(
                "\nEnter the job description file path: "
            ).strip()

            job = extract_requirements_from_file(file_path)

        else:

            print("Invalid choice.")
            return

        display_job_description(job)

    except Exception as error:

        print(f"\nERROR: {error}")


if __name__ == "__main__":
    main()


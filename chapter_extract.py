import json
import pdfplumber
import fitz
import re

# Function to extract text from the PDF
def extract_text_from_pdf(pdf_file, contents):
    body_page = []
    for i in contents:
        body_page.append(i[2])

    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            if page.page_number in body_page:
                text += page.extract_text()
    return text

def _prepare_regex(title: str) -> str:
        """
        Escapes special characters and replaces spaces with '\\s*' for regex usage.
        """
        return re.escape(title).replace('\\ ', '\\s*')

# Function to map sections to extracted text
def map_text_to_sections(structure, pdf_text):
    section_texts = []
    titles = []

    # Loop through the structure.json contents
    for chapter_number, chapter_data in structure.items():

        chapter_title_regex = _prepare_regex(chapter_data.get('title', ''))
        chapter_regex = rf"(?i)Глава\s*{chapter_number}\s*{chapter_title_regex}"
        match = re.search(chapter_regex, pdf_text)
        if match:
            chapter_start = match.start()
            chapter_end = match.end()
            titles.append(pdf_text[chapter_start:chapter_end])

        sections = chapter_data.get('sections')
        for section_number, section_data in sections.items():
            section_regex = _prepare_regex(section_data.get('title', ''))
            section_regex = rf"(?i){section_number}\s*{section_regex}"
            match = re.search(section_regex, pdf_text)
            if match:
                section_start = match.start()
                section_end = match.end()
                titles.append(pdf_text[section_start:section_end])

            subsections = section_data.get('subsections')
            for subsection_number, subsection_data in subsections.items():
                subsection_regex = _prepare_regex(subsection_data.get('title', ''))
                subsection_regex = rf"(?i){subsection_number}\s*{subsection_regex}"
                match = re.search(subsection_regex, pdf_text)
                if match:
                    subsection_start = match.start()
                    subsection_end = match.end()
                    titles.append(pdf_text[subsection_start:subsection_end])

    for i in range(len(titles)-1):
        start_idx = pdf_text.find(titles[i])
        next_title = titles[i+1]
        if next_title is None:
            next_idx=len(pdf_text)
        next_idx = pdf_text.find(next_title)
        #print('start idx: {}, current title: {}, next idx: {}, next title: {}'.format(start_idx, next_idx, chapter_titles[i], chapter_titles[i+1]))
        section_text = pdf_text[start_idx:next_idx].strip()
        section_texts.append({"title": titles[i], "text": section_text})

    return section_texts

# Function to save section texts as json
def save_sections_to_json(sections, output_file):
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(sections, json_file, ensure_ascii=False, indent=4)


# Main process
def process_pdf_to_json(pdf_file, structure_file, output_file):
    # Load the structure.json
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)

    #table of contents
    doc = fitz.open(pdf_file)
    contents = doc.get_toc()
    #print(contents)

    # Extract the text from the PDF
    pdf_text = extract_text_from_pdf(pdf_file, contents)

    # Map sections to their corresponding text
    result = map_text_to_sections(structure, pdf_text)

    # Save the result to a JSON file
    save_sections_to_json(result, output_file)


# Example usage
pdf_file = 'book.pdf'
structure_file = 'structure.json'
output_file = 'output_chapters.json'

process_pdf_to_json(pdf_file, structure_file, output_file)

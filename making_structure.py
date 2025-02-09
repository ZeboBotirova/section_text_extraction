import PyPDF2
import pdfplumber
import fitz
import re
import json


def extract_toc_from_pdf(pdf, titles=None):
    if titles is None:
        titles = []

    for title in pdf:
        if isinstance(title, dict) and '/Title' in title:
            titles.append(title['/Title'])
        elif isinstance(title, list):
            # Recursively call the function if the element is a list
            extract_toc_from_pdf(title, titles)

    return titles

def _prepare_regex(title: str) -> str:
        """
        Escapes special characters and replaces spaces with '\\s*' for regex usage.
        """
        return re.escape(title).replace('\\ ', '\\s*')


def _chapter_titles(pdf_text, structure):
    chapter_titles = []
    for chapter_number, chapter_data in structure.items():
        chapter_titles.append(chapter_data.get('title'))
        chapter_title_regex = _prepare_regex(chapter_data.get('title', ''))
        chapter_regex = rf"(?i)Глава\s*{chapter_number}\s*{chapter_title_regex}"
        match = re.search(chapter_regex, pdf_text)
        if match:
            chapter_start = match.start()
            chapter_end = match.end()
            chapter_titles.append(pdf_text[chapter_start:chapter_end])
            # return chapter_titles
        # else:
        # return None
    # print('chapter data: ', chapter_data)

    return chapter_titles


def _section_titles(pdf_text, structure):
    section_titles = []
    for chapter_number, chapter_data in structure.items():
        sections = chapter_data.get('sections')
        for section_number, section_data in sections.items():
            #print("sectiondataend", section_data.get('end'))
            section_regex = _prepare_regex(section_data.get('title', ''))
            section_regex = rf"(?i){section_number}\s*{section_regex}"
            match = re.search(section_regex, pdf_text)
            if match:
                section_start = match.start()
                print("sectionstart: ", section_start)
                section_end = match.end()
                print("sectionend: ", section_end)
                section_titles.append(pdf_text[section_start:section_end])
                #if section_end is None:
                #   section_titles.append(pdf_text[section_start:])


    return section_titles


def _subsection_titles(pdf_text, structure):
    subsection_titles = []
    for chapter_number, chapter_data in structure.items():
        sections = chapter_data.get('sections')
        # print('Chapter data: ', chapter_data)
        # print('Section.item ', sections.items())
        for section_number, section_data in sections.items():
            # print('Section data: ', section_data)
            subsections = section_data.get('subsections')
            for subsection_number, subsection_data in subsections.items():
                subsection_regex = _prepare_regex(subsection_data.get('title', ''))
                subsection_regex = rf"(?i){subsection_number}\s*{subsection_regex}"
                match = re.search(subsection_regex, pdf_text)
                if match:
                    subsection_start = match.start()
                    subsection_end = match.end()
                    subsection_titles.append(pdf_text[subsection_start:subsection_end])
                    # return subsection_titles
            # else:
            # return None
    return subsection_titles

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


def check_if_chapter(text):
    # Regext pattern to extract chapter number
    chapter_pattern = r"Глава\s*(\d+)"

    match = re.search(chapter_pattern, text)

    if match:
        return match.group(1)
    else:
        return None


def check_if_section(text):
    # check if text is a section. It is section when it starts with a section number
    if text[0].isdigit() and ' ' in text:
        section_number, section_title = text.split(' ', 1)

        # Remove a dot at the end if it exists
        section_number = section_number.rstrip('.')
        section_title = section_title.rstrip()

        return section_number, section_title
    else:
        return None, None

def parse_titles(toc, pdf_text, chapter_titles, section_titles, subsection_titles):
    result = {}
    current_chapter = None
    sec_titles = []
    subsec_titles = []
    # The example book chapter title comes after "Глава". When "Глава" is present in the "title",
    # then the next "title" contains chapter title.
    for tit in section_titles:
        if tit[0].isdigit() and " " in tit:
            sec_num, sec_title = tit.split(" ", 1)
            sec_num = sec_num.rstrip('.')
            sec_title = sec_title.rstrip()
            sec_titles.append(sec_title.replace("\n", " "))
    print('sec_titles: ', sec_titles)

    for subtit in subsection_titles:
        for n in range(len(subtit)-1):
            if subtit[n].isdigit() and subtit[n+1].isalpha():
                subtit = subtit.replace(subtit[n+1], " "+subtit[n+1])
        if subtit[0].isdigit() and " " in subtit:
            sec_num, sec_title = subtit.split(" ", 1)
            subsec_num = sec_num.rstrip('.')
            subsec_title = sec_title.rstrip()
            # print(subsec_title)
            subsec_titles.append(subsec_title.replace("\n", " "))

    #print('subsec_titles: ', subsec_titles)

    skip = False

    for idx, title in enumerate(toc):

        # skip the title because it is chapter name
        if skip:
            skip = False
            continue

        chapter_num = check_if_chapter(title)

        if chapter_num:
            chapter_title = toc[idx + 1]
            i = chapter_titles.index(chapter_title)
            start_idx = pdf_text.find(chapter_titles[i])
            end_idx = pdf_text.find(chapter_titles[i+1])
            chapter_text = pdf_text[start_idx:end_idx].strip()
            result[chapter_num] = {"title": chapter_title, "sections": {}, "text": chapter_text.replace("\n", " ")}
            current_chapter = chapter_num
            skip = True
            #continue
        else:
            section_number, section_title = check_if_section(title)
            #section_title = " ".join(section_title.split())

            if section_number:

                parts = section_number.split('.')
                print('Parts: ',parts)
                if len(parts) == 2:  # Section
                    section_title = " ".join(section_title.split())
                    j = sec_titles.index(section_title.upper())
                    if j < (len(section_titles)-1):
                    #   end_idx=len(pdf_text)
                        start_idx = pdf_text.find(section_titles[j])
                        end_idx = pdf_text.find(section_titles[j+1])
                        section_text = pdf_text[start_idx:end_idx].strip()

                    # check if section already exists
                    if section_number in result[current_chapter]["sections"]:
                        section_number += '.'
                    result[current_chapter]["sections"][section_number] = {
                                "title": section_title,
                                "subsections": {},
                            "text": section_text.replace("\n", " ")
                    }



                elif len(parts) >= 3:  # Subsection
                    section_title = " ".join(section_title.split())
                    l = subsec_titles.index(section_title.strip())
                    if l < (len(subsec_titles)-1):
                        start_idx = pdf_text.find(subsection_titles[l])
                        end_idx = pdf_text.find(subsection_titles[l+1])
                        subsection_text = pdf_text[start_idx:end_idx].strip()
                    parent_section = '.'.join(parts[:2])
                    #parent_section = '.'.join(section_number[:2])
                    result[current_chapter]["sections"][parent_section]["subsections"][section_number] = {
                        "title": section_title, "text": subsection_text.replace("\n", " ")

                    }
            continue
    return result


file_path = 'book.pdf'
output_path = 'output.json'
structure_file = 'structure.json'

# Open the PDF file
pdf = PyPDF2.PdfReader(file_path)
#table of contents
doc = fitz.open(file_path)
contents = doc.get_toc()

# Extract the text from the PDF
pdf_text = extract_text_from_pdf(file_path, contents)


# Load the structure.json
with open(structure_file, 'r', encoding='utf-8') as f:
    structure = json.load(f)

chapter_titles = _chapter_titles(pdf_text, structure)
section_titles = _section_titles(pdf_text, structure)
print('Section titles: ', section_titles)
subsection_titles = _subsection_titles(pdf_text, structure)
print('Subsection titles: ',subsection_titles)

print('Extracting text from PDF file...')
toc = extract_toc_from_pdf(pdf.outline)
#print('Titles: ', toc)
print('Processing text from PDF...')
result = parse_titles(toc, pdf_text, chapter_titles, section_titles, subsection_titles)
#print(result)
print('Writing result to file...')



with open(output_path, 'w', encoding='utf-8') as json_file:
    json.dump(result, json_file, ensure_ascii=False, indent=4)

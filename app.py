from flask import Flask, render_template, request, send_file, redirect, url_for
from pybtex.database import parse_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("Nenhum arquivo encontrado.")
        return redirect(request.url)

    file = request.files['file']
    custom_filename = request.form.get('filename')  

    if file.filename == '':
        print("Nenhum arquivo foi selecionado.")
        return redirect(request.url)

    if file and file.filename.endswith('.bib'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            bib_data = parse_file(file_path)
            bib_entries = bib_data.entries.values()
        except Exception as e:
            print(f"Erro ao processar o arquivo BibTeX: {e}")
            return "Erro ao processar o arquivo BibTeX", 500


        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{custom_filename}.pdf')  

        try:
            generate_sorted_pdf(bib_entries, pdf_path)
        except Exception as e:
            print(f"Erro ao gerar PDF: {e}")
            return "Erro ao gerar PDF", 500

        return send_file(pdf_path, as_attachment=True, download_name=f'{custom_filename}.pdf')  

    print("Arquivo enviado não é um arquivo BibTeX válido.")
    return redirect(request.url)

def generate_sorted_pdf(bib_entries, file_path):
    categorized_entries = {
        'article': [],
        'book': [],
        'inproceedings': [],
        'misc': [],
        'magazine': [],
        'journal': []
    }

    
    for entry in bib_entries:
        entry_type = entry.type
        if entry_type in categorized_entries:
            categorized_entries[entry_type].append(entry)
        else:
            categorized_entries['misc'].append(entry)

    
    for key in categorized_entries:
        categorized_entries[key].sort(key=lambda x: x.fields.get('title', '').lower())

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    margin = 50
    y_position = height - margin

   
    c.setFont("Helvetica", 12)

    def add_section_title(c, title, y_position):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_position, title)
        c.setFont("Helvetica", 12)
        return y_position - 30

    def add_entry(c, entry, y_position):
        title = entry.fields.get('title', 'No Title')
        authors = entry.persons.get('author', [])
        if authors:
            author_names = " and ".join(str(author) for author in authors)
        else:
            author_names = "Unknown Author"

        
        text_title = f"Title: {title}"
        text_authors = f"Authors: {author_names}"

        lines_title = split_text(c, text_title, width - 2 * margin)
        lines_authors = split_text(c, text_authors, width - 2 * margin)

        for line in lines_title:
            c.drawString(margin, y_position, line)
            y_position -= 15
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - margin

        for line in lines_authors:
            c.drawString(margin, y_position, line)
            y_position -= 15
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - margin

        y_position -= 10
        if y_position < margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - margin

        return y_position

    def split_text(c, text, max_width):
        lines = []
        words = text.split(' ')
        line = ""
        for word in words:
            if c.stringWidth(line + word + ' ') < max_width:
                line += word + ' '
            else:
                if line:
                    lines.append(line.strip())
                line = word + ' '
        if line:
            lines.append(line.strip())
        return lines

    for category, title in [('article', 'Artigos'), ('book', 'Livros'), ('inproceedings', 'Periódicos'), ('misc', 'Outros'), ('magazine', 'revistas'), ('journal', 'Jornais')]:
        if categorized_entries[category]:
            y_position = add_section_title(c, title, y_position)
            for entry in categorized_entries[category]:
                y_position = add_entry(c, entry, y_position)
                if y_position < margin:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y_position = height - margin

    c.save()

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

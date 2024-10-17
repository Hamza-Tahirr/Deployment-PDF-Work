from flask import Flask, request, send_file, render_template, url_for, send_from_directory
import fitz  # PyMuPDF
import os
import re
from PIL import Image
import io

app = Flask(__name__)

# Set max upload size to 100 MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_circle(bbox):
    """Check if the bounding box is circular and larger than 30px."""
    width = bbox.x1 - bbox.x0
    height = bbox.y1 - bbox.y0
    return width > 30 and height > 30 and abs(width - height) < 5

def save_image(image_data, image_name):
    """Save image bytes to the uploads directory with the name from the PDF."""
    image = Image.open(io.BytesIO(image_data))
    # Resize image to 100x100 pixels
    image = image.resize((100, 100))
    image_path = os.path.join(UPLOAD_FOLDER, f'{image_name}.png')
    image.save(image_path)
    return image_path

def redact_names_and_individuals(page, name_pattern, word_to_remove):
    """Redact names and the word 'Individual' from the page."""
    text = page.get_text("text")
    names_on_page = []
    for match in name_pattern.finditer(text):
        first_name = match.group(2)
        last_name = match.group(1)
        new_name = f"{first_name} {last_name}"  # Rearrange name
        names_on_page.append(new_name)
        for inst in page.search_for(match.group()):
            page.add_redact_annot(inst, fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_text(inst[:2], new_name, fontsize=11, fontname="helv")

    for inst in page.search_for(word_to_remove):
        page.add_redact_annot(inst, fill=(1, 1, 1))
        page.apply_redactions()
        page.insert_text(inst[:2], " ", fontsize=11, fontname="helv")
    
    return names_on_page

def extract_images_from_page(doc, page, image_names):
    """Extract images from a page using provided names."""
    images_on_pages = []
    image_index = 0
    for img in page.get_images(full=True):
        xref = img[0]
        img_bbox = fitz.Rect(page.get_image_bbox(img))
        base_image = doc.extract_image(xref)
        image_data = base_image["image"]
        
        if image_index < len(image_names):
            image_name = image_names[image_index]
        else:
            image_name = f"Unnamed_{image_index + 1}"
        
        image_path = save_image(image_data, image_name)
        
        images_on_pages.append({
            'x0': img_bbox.x0,
            'y0': img_bbox.y0,
            'x1': img_bbox.x1,
            'y1': img_bbox.y1,
            'image_path': image_path,
            'image_name': image_name
        })
        
        image_index += 1
        
    return images_on_pages

def extract_text_below_images(page):
    """Extract text below images on a given page."""
    text_below_images = []
    text = page.get_text('text')
    lines = text.split('\n')
    
    for line in lines:
        if line.strip():  # Only process non-empty lines
            text_below_images.append(line.strip())
    
    return text_below_images

def process_pdf(input_pdf_path, output_pdf_path):
    """Replace names and extract circular images from PDF."""
    doc = fitz.open(input_pdf_path)
    name_pattern = re.compile(r'(\b[A-Z][a-zA-Z]+), ([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)')
    word_to_remove = "Individual"
    
    images_on_pages = []

    for page_num, page in enumerate(doc):
        names_on_page = redact_names_and_individuals(page, name_pattern, word_to_remove)
        page_images = extract_images_from_page(doc, page, names_on_page)

        # Extract text below images and pair it with corresponding images
        texts_below_images = extract_text_below_images(page)
        
        for i in range(len(page_images)):
            if i < len(texts_below_images):
                page_images[i]['text_below'] = texts_below_images[i]  # Pairing text with images
            
            # Adding checkbox above each image
            checkbox_rect = fitz.Rect(page_images[i]['x0'], page_images[i]['y0'] - 20,
                                       page_images[i]['x0'] + 15, page_images[i]['y0'])
            
            # Create a checkbox widget and set it as checked ("Yes")
            checkbox_widget = fitz.Widget()
            checkbox_widget.rect = checkbox_rect
            checkbox_widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            checkbox_widget.field_name = f"checkbox_{page_num}_{i}"
            checkbox_widget.field_value = "Yes"  # Default state of checkbox is "Yes" (checked)
            
            # Add widget to the current page using add_widget method
            page.add_widget(checkbox_widget)

        images_on_pages.extend([{'page': page_num, **img} for img in page_images])

    doc.save(output_pdf_path)
    doc.close()
    
    return images_on_pages


@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    
    if not file or not file.filename:
        return "No selected file", 400

    input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    output_pdf_path = os.path.join(UPLOAD_FOLDER, f'modified_{file.filename}')
    
    file.save(input_pdf_path)

    images_on_pages = process_pdf(input_pdf_path, output_pdf_path)

    return render_template('display.html', 
                           pdf_url=url_for('serve_pdf', filename=f'modified_{file.filename}'),
                           images=images_on_pages,
                           filename=f'modified_{file.filename}')

@app.route('/uploads/<filename>')
def serve_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/image/<image_name>')
def serve_image(image_name):
    return send_from_directory(UPLOAD_FOLDER, image_name)

@app.route('/remove')
def remove():
    return render_template('remove.html')

@app.route('/remove_upload', methods=['POST'])
def remove_upload():
    file = request.files.get('file')
    
    if not file or not file.filename:
        return "No selected file", 400
    
    input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    
    file.save(input_pdf_path)
    
    doc = fitz.open(input_pdf_path)
    
    # Determine the number of pages in the PDF
    total_pages = len(doc)
    
    for page_num in range(total_pages):
        page = doc[page_num]
        
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX and widget.field_value == "Yes":
                checkbox_rect = widget.rect
                
                img_rects_to_remove = []
                text_below_img_rects_to_remove = []

                for img in page.get_images(full=True):
                    xref = img[0]
                    img_bbox = fitz.Rect(page.get_image_bbox(img))
                    
                    if img_bbox.intersects(checkbox_rect):
                        img_rects_to_remove.append(img_bbox)

                        text_below_rect = fitz.Rect(img_bbox.x0, img_bbox.y1, img_bbox.x1, img_bbox.y1 + 30)
                        text_instances = page.get_text("text", clip=text_below_rect)
                        
                        if text_instances.strip():  
                            text_below_img_rects_to_remove.append(text_below_rect)

                for img_rect in img_rects_to_remove:
                    page.add_redact_annot(img_rect, fill=(1, 1, 1)) 

                for text_rect in text_below_img_rects_to_remove:
                    page.add_redact_annot(text_rect, fill=(1, 1, 1)) 
                
                # Check the number of pages and apply different whiteout sizes accordingly
                if total_pages <= 4:
                    whiteout_rect = fitz.Rect(checkbox_rect.x0, checkbox_rect.y1, checkbox_rect.x0 + 100, checkbox_rect.y1 + 70)
                else:
                    whiteout_rect = fitz.Rect(checkbox_rect.x0, checkbox_rect.y1, checkbox_rect.x0 + 120, checkbox_rect.y1 + 120)
                
                page.add_redact_annot(whiteout_rect, fill=(1, 1, 1))  # Apply white rectangle

        page.apply_redactions()

    final_output_pdf_path = os.path.join(UPLOAD_FOLDER, f'final_{file.filename}')
    doc.save(final_output_pdf_path)  
    doc.close()
    
    # Check if the file is saved correctly
    if not os.path.exists(final_output_pdf_path):
        return "Error processing PDF", 500
    
    return render_template('final.html', pdf_url=url_for('serve_pdf', filename=f'final_{file.filename}'))

@app.route('/final/<filename>')
def final(filename):
   return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
   app.run(debug=True, port=5001)

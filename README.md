# PDF Photo Roster Editor

A small Flask web app for cleaning up photo roster PDFs, meaning documents that show a grid of portrait photos with a name under each one. It reformats the names, pulls out the photos, and lets you tick which photos should be removed from the final PDF.

No sample PDFs are included, so you need your own roster PDF to try it.

## Features

- Upload a PDF and have every `Last, First` name rewritten as `First Last` in place.
- Remove the word `Individual` from the pages. Some roster exports print it under every entry.
- Extract every photo on each page, resize it to 100x100 and save it as a PNG named after the person. Names are matched to photos in the order they appear on the page, and photos without a name are saved as `Unnamed_<n>.png`.
- Add a checkbox above each photo in the modified PDF. All boxes start ticked.
- Upload the edited PDF again: every photo whose box is still ticked is covered in white along with the name directly below it. The final PDF can then be viewed or downloaded.

## Tech stack

- Python, Flask
- PyMuPDF for reading, redacting and editing PDFs
- Pillow for resizing the extracted photos
- Bootstrap 5 (CDN) for the HTML templates
- gunicorn for production

## Project structure

```
app.py              Flask app and all PDF processing
templates/
  upload.html       step 1: upload the original PDF
  display.html      shows the modified PDF with checkboxes
  remove.html       step 2: upload the edited PDF
  final.html        shows and downloads the final PDF
requirements.txt
Procfile            gunicorn entry for Procfile-based hosts
```

Uploaded files, extracted photos and output PDFs go into an `uploads/` folder next to `app.py`. The app creates this folder when it starts, and git ignores it.

## Setup

The project was built with Python 3.12.

```bash
git clone https://github.com/Hamza-Tahirr/Deployment-PDF-Work.git
cd Deployment-PDF-Work
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Open http://localhost:5000 in your browser. You can set these environment variables:

- `PORT` sets the port (default `5000`)
- `FLASK_DEBUG=1` turns on Flask debug mode

For production, the `Procfile` starts the app with gunicorn:

```bash
gunicorn app:app
```

## Usage

1. On the home page, upload the original roster PDF.
2. The modified PDF opens in the browser. Untick the photos you want to keep and save the PDF.
3. Click **Remove PDF** and upload the saved file.
4. The final PDF, without the ticked photos, opens and can be downloaded.

## License

MIT, see [LICENSE](LICENSE).

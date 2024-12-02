import sys
from flask import Flask, request, jsonify, render_template
import os
import fitz 
import requests
import webbrowser  
from werkzeug.utils import secure_filename
from pathlib import Path
from threading import Thread
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPalette, QColor

IMGUR_CLIENT_ID = "YOUR_CLIENT_ID"

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SYSTEM_DOWNLOAD_FOLDER = str(Path.home() / "Downloads")

def allowed_file(filename):
    """Проверяет, разрешен ли файл для загрузки"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(folder, base_filename):
    """Получение уникального имени файла"""
    counter = 1
    filename = f"{base_filename}_{counter}.png"
    while os.path.exists(os.path.join(folder, filename)):
        counter += 1
        filename = f"{base_filename}_{counter}.png"
    return filename

def upload_to_imgur(image_path):
    """Загрузка изображения на Imgur"""
    headers = {
        "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
    }
    try:
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                "https://api.imgur.com/3/upload",
                headers=headers,
                files={'image': image_file}
            )
        if response.status_code == 200:
            data = response.json()
            imgur_link = data['data']['link']
            webbrowser.open_new_tab(imgur_link) 
            return imgur_link
        else:
            return None
    except Exception as e:
        print(f"Ошибка загрузки на Imgur: {e}")
        return None

def convert_pdf_to_png(pdf_path, output_folder):
    """Конвертация PDF в PNG"""
    converted_files = []
    imgur_links = []
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(dpi=400)
            
            base_filename = os.path.splitext(os.path.basename(pdf_path))[0] + f"_page_{page_num + 1}"
            image_filename = get_unique_filename(output_folder, base_filename)
            image_path = os.path.join(output_folder, image_filename)
            pix.save(image_path)
            converted_files.append(image_path)
            
            imgur_link = upload_to_imgur(image_path)
            if imgur_link:
                imgur_links.append(imgur_link)
        
        pdf_document.close()
    except Exception as e:
        raise RuntimeError(f"Ошибка при конвертации: {e}")
    return converted_files, imgur_links

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Нет файла"}), 400

    file = request.files['file']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            converted_files, imgur_links = convert_pdf_to_png(
                file_path,
                app.config['UPLOAD_FOLDER']
            )
            response = {
                "imgur_links": imgur_links,
                "saved_files": [os.path.basename(f) for f in converted_files]
            }
            return jsonify(response), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Недопустимый файл"}), 400

def run_flask():
    app.run(debug=True, use_reloader=False, threaded=True)

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF to PNG Converter")
        self.setGeometry(100, 100, 1200, 800)

        icon_path = 'icon.ico'
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))  
        else:
            print(f"Иконка не найдена: {icon_path}")

        self.set_dark_theme()

        self.setFixedSize(450, 400) 

        self.setWindowIcon(QIcon('C:/Users/justi/Downloads/docx/icon.ico'))

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("http://127.0.0.1:5000/"))

        layout = QVBoxLayout()
        layout.addWidget(self.browser)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def set_dark_theme(self):
        """Настройка темной темы для приложения"""
        app_palette = QPalette()
        
        app_palette.setColor(QPalette.Background, QColor(53, 53, 53))
        app_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        app_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        app_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        app_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        app_palette.setColor(QPalette.Highlight, QColor(255, 0, 127))
        app_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        self.setPalette(app_palette)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
                color: white;
            }
            QMenuBar {
                background-color: #353535;
                color: white;
            }
            QMenuBar::item {
                background: transparent;
                padding: 5px;
            }
            QMenuBar::item:selected {
                background-color: #555555;
            }
        """)

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    qt_app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(qt_app.exec_())

# -*- coding: utf-8 -*-
import os, requests, warnings, io, webview, re
from flask import Flask, render_template_string, request, redirect, jsonify, send_file
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
from PIL import Image
from threading import Thread

warnings.filterwarnings('ignore', category=UserWarning)
app = Flask(__name__)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(CUR_DIR, 'library')
CACHE_PATH = os.path.join(CUR_DIR, 'cache')
for p in [LIB_PATH, CACHE_PATH]:
    if not os.path.exists(p): os.makedirs(p)

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&display=swap');
body { 
    background-color: #f4ecd8; color: #5b4636; font-family: 'Lora', serif; 
    margin: 0; padding: 0; overflow: hidden; user-select: none; 
}

/* БИБЛИОТЕКА */
.main-container { height: 100vh; display: flex; flex-direction: column; }
.shelf-grid { 
    flex: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); 
    gap: 25px; padding: 30px; overflow-y: auto; margin-top: 65px;
}
.book-card { 
    background: #fffdf9; padding: 12px; border-radius: 10px; text-align: center; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-decoration: none; color: inherit; 
    transition: 0.3s; height: 380px; display: flex; flex-direction: column; cursor: pointer;
}
.book-card:hover { transform: translateY(-8px); box-shadow: 0 12px 25px rgba(0,0,0,0.12); }
.book-card img { width: 100%; height: 240px; object-fit: cover; border-radius: 5px; margin-bottom: 8px; }

/* ЧИТАЛКА */
#viewer-outer {
    position: relative; width: 100vw; height: calc(100vh - 105px);
    margin-top: 60px; display: flex; justify-content: center;
}
#viewer-container {
    width: 850px; height: 100%; overflow: hidden; position: relative;
}
#actual-content {
    height: 100%;
    column-width: 850px; column-gap: 0px; column-fill: auto;
    transition: transform 0.6s ease-in-out;
    text-align: justify; line-height: 1.7; font-size: 21px; box-sizing: border-box;
}

#actual-content img { max-width: 100%; height: auto; display: block; margin: 15px auto; border-radius: 5px; }

.toolbar { 
    background: #efe4cb; height: 60px; display: flex; justify-content: space-between; 
    align-items: center; border-bottom: 1px solid #d3c6a8; padding: 0 20px; 
    position: fixed; top: 0; left: 0; right: 0; z-index: 200;
}
.toolbar button { background: #5b4636; color: white; border: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; }

#resume-modal {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
    background: #fffdf9; padding: 30px; border-radius: 15px; border: 2px solid #5b4636;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4); z-index: 1000; display: none; text-align: center;
}

.footnote-tooltip { 
    position: fixed; display: none; background: #fffdf9; border-left: 5px solid #5b4636; 
    padding: 18px; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); 
    z-index: 1000; max-width: 400px; font-size: 16px; line-height: 1.5; pointer-events: none;
}
.page-footer { position: fixed; bottom: 0; left: 0; right: 0; background: #efe4cb; height: 45px; display: flex; align-items: center; justify-content: center; font-size: 13px; z-index: 150; border-top: 1px solid #d3c6a8; }
"""

@app.route('/')
def index():
    books = []
    for f in os.listdir(LIB_PATH):
        if f.endswith('.epub'):
            try:
                b = epub.read_epub(os.path.join(LIB_PATH, f))
                title = b.get_metadata('DC', 'title')[0][0] if b.get_metadata('DC', 'title') else f
                author = b.get_metadata('DC', 'creator')[0][0] if b.get_metadata('DC', 'creator') else "Автор"
                books.append({'file': f, 'title': title, 'author': author})
            except: books.append({'file': f, 'title': f, 'author': 'Error'})
    
    cards = "".join([f'''
        <div class="book-card" onclick="checkBookResume('{b["file"]}')">
            <img src="/cover/{b["file"]}">
            <div style="font-size:13px; margin-top:5px;"><b>{b["author"]}</b><br>{b["title"]}</div>
        </div>''' for b in books])
    
    return render_template_string(f"""
    <html><head><style>{STYLE}</style></head>
    <body>
        <div id="resume-modal">
            <h3>Продолжить чтение?</h3>
            <p id="resume-info"></p>
            <button id="btn-resume" style="background:#5b4636; color:white; padding:10px 20px; border:none; border-radius:20px;">Да, продолжить</button>
            <button id="btn-start-over" style="background:none; border:1px solid #ccc; padding:10px 20px; border-radius:20px; margin-left:10px;">Сначала</button>
        </div>
        <div class="main-container">
            <div class="toolbar"><b>📚 Моя Библиотека</b>
                <form action="/add" method="post" style="display:flex; gap:10px;">
                    <input name="url" placeholder="ID Flibusta" style="border-radius:15px; border:1px solid #d3c6a8; padding:5px 15px;">
                    <button type="submit">Добавить</button>
                </form>
            </div>
            <div class="shelf-grid">{cards}</div>
        </div>
        <script>
            function checkBookResume(file) {{
                const data = JSON.parse(localStorage.getItem('save_' + file) || 'null');
                if (data) {{
                    document.getElementById('resume-modal').style.display = 'block';
                    document.getElementById('resume-info').innerText = "Остановка на странице " + (data.page + 1);
                    document.getElementById('btn-resume').onclick = () => location.href = "/read/" + file + "?part=" + data.part + "&resume=1";
                    document.getElementById('btn-start-over').onclick = () => location.href = "/read/" + file + "?part=0";
                }} else {{
                    location.href = "/read/" + file + "?part=0";
                }}
            }}
        </script>
    </body></html>
    """)

@app.route('/read/<filename>')
def read_book(filename):
    part = int(request.args.get('part', 0))
    book = epub.read_epub(os.path.join(LIB_PATH, filename))
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else filename
    
    spine = [item[0] for item in book.spine if item[0] != 'nav']
    docs = [book.get_item_with_id(s) for s in spine if book.get_item_with_id(s) and book.get_item_with_id(s).get_type() == ebooklib.ITEM_DOCUMENT]
    
    if part >= len(docs): part = len(docs) - 1
    soup = BeautifulSoup(docs[part].get_content().decode('utf-8', 'ignore'), 'html.parser')

    # Прокси для картинок
    for img in soup.find_all(['img', 'image']):
        src = (img.get('src') or img.get('xlink:href') or "").split('/')[-1]
        img['src'] = f"/img_proxy/{filename}/{src}"

    return render_template_string(f"""
    <html><head><style>{STYLE}</style></head>
    <body onload="initReader()">
        <div id="tooltip" class="footnote-tooltip"></div>
        <div class="toolbar">
            <div style="max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                <button onclick="location.href='/'">🏠</button>
                <span style="margin-left:10px; font-weight:bold;">{title}</span>
                <span style="margin-left:10px; opacity:0.7;">| Глава {part+1}</span>
            </div>
            <div>
                <button onclick="changeFS(1)">A+</button><button onclick="changeFS(-1)" style="margin-left:5px;">A-</button>
            </div>
        </div>

        <div id="viewer-outer">
            <div id="viewer-container"><div id="actual-content">{str(soup)}</div></div>
        </div>

        <div class="page-footer">стр.&nbsp;<span id="cur-p">1</span>&nbsp;из&nbsp;<span id="total-p">1</span></div>

        <script>
            let currentPage = 0, totalPages = 1;
            const filename = "{filename}", part = {part};

            function updatePagination(targetPage = -1) {{
                const content = document.getElementById('actual-content');
                const container = document.getElementById('viewer-container');
                totalPages = Math.ceil(content.scrollWidth / container.clientWidth) || 1;
                document.getElementById('total-p').innerText = totalPages;
                
                if (targetPage !== -1) currentPage = targetPage;
                else if (window.location.search.includes('resume=1')) {{
                    const data = JSON.parse(localStorage.getItem('save_' + filename));
                    if(data) currentPage = data.page || 0;
                }}
                renderPage();
            }}

            function renderPage() {{
                const container = document.getElementById('viewer-container');
                const content = document.getElementById('actual-content');
                content.style.transform = `translateX(-${{currentPage * container.clientWidth}}px)`;
                document.getElementById('cur-p').innerText = currentPage + 1;
                // Сохраняем при каждом сдвиге
                localStorage.setItem('save_' + filename, JSON.stringify({{part: part, page: currentPage}}));
            }}

            function movePage(d) {{
                if(d===1 && currentPage < totalPages-1) {{ currentPage++; renderPage(); }}
                else if(d===-1 && currentPage > 0) {{ currentPage--; renderPage(); }}
                else if(d===1) location.href=`/read/${{filename}}?part=${{part+1}}&resume=1`; // чтобы сбросилось на 0 при переходе
                else if(d===-1 && part > 0) location.href=`/read/${{filename}}?part=${{part-1}}`;
            }}

            // КНОПКИ КЛАВИАТУРЫ
            document.addEventListener('keydown', (e) => {{
                if (e.key === "ArrowRight") movePage(1);
                if (e.key === "ArrowLeft") movePage(-1);
            }});

            async function initReader() {{
                const s = localStorage.getItem('fsize');
                if(s) document.getElementById('actual-content').style.fontSize = s;
                
                const r = await fetch('/get_notes/'+filename);
                const notes = await r.json();

                document.querySelectorAll('#actual-content a').forEach(a => {{
                    const id = (a.getAttribute('href') || "").split('#')[1];
                    if(notes[id]) {{
                        a.onmouseenter = (e) => {{
                            const t = document.getElementById('tooltip');
                            t.innerHTML = notes[id];
                            t.style.display = 'block';
                            t.style.left = Math.min(e.clientX, window.innerWidth - 420) + 'px';
                            t.style.top = (e.clientY + 20) + 'px';
                        }};
                        a.onmouseleave = () => document.getElementById('tooltip').style.display='none';
                        a.onclick = (e) => e.preventDefault();
                    }}
                }});
                setTimeout(updatePagination, 300);
            }}

            function changeFS(d) {{
                const content = document.getElementById('actual-content');
                const container = document.getElementById('viewer-container');
                
                // Находим текущий центр страницы для "якоря"
                const oldWidth = content.scrollWidth;
                const progress = (currentPage * container.clientWidth) / oldWidth;

                content.style.transition = 'none';
                content.style.fontSize = (parseInt(window.getComputedStyle(content).fontSize)+d)+'px';
                localStorage.setItem('fsize', content.style.fontSize);
                
                setTimeout(() => {{
                    const newTotal = Math.ceil(content.scrollWidth / container.clientWidth) || 1;
                    currentPage = Math.round(progress * newTotal);
                    updatePagination(currentPage);
                    setTimeout(() => content.style.transition = 'transform 0.6s ease-in-out', 50);
                }}, 50);
            }}
        </script>
    </body></html>
    """)

@app.route('/img_proxy/<filename>/<path:imgname>')
def img_proxy(filename, imgname):
    try:
        book = epub.read_epub(os.path.join(LIB_PATH, filename))
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            if imgname in item.get_name():
                return send_file(io.BytesIO(item.get_content()), mimetype='image/jpeg')
    except: pass
    return "404", 404

@app.route('/cover/<filename>')
def get_cover(filename):
    cache_file = os.path.join(CACHE_PATH, f"cv_{filename}.webp")
    if os.path.exists(cache_file): return send_file(cache_file)
    try:
        book = epub.read_epub(os.path.join(LIB_PATH, filename))
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            if 'cover' in item.get_name().lower():
                img = Image.open(io.BytesIO(item.get_content())).convert('RGB')
                img.thumbnail((300, 450)); img.save(cache_file, "WEBP")
                return send_file(cache_file)
    except: pass
    return "No Cover", 404

@app.route('/get_notes/<filename>')
def get_notes(filename):
    try:
        book = epub.read_epub(os.path.join(LIB_PATH, filename))
        notes = {}
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            for el in soup.find_all(True, id=True):
                txt = el.get_text(" ", strip=True)
                if len(txt) > 5: notes[el['id']] = txt
        return jsonify(notes)
    except: return jsonify({})

@app.route('/add', methods=['POST'])
def add_book():
    bid = "".join(filter(str.isdigit, request.form.get('url', '')))
    if bid:
        try:
            r = requests.get(f"https://flibusta.is/b/{bid}/epub", headers={'User-Agent':'Mozilla/5.0'}, verify=False)
            if r.status_code == 200:
                with open(os.path.join(LIB_PATH, f"{bid}.epub"), 'wb') as f: f.write(r.content)
        except: pass
    return redirect('/')

if __name__ == '__main__':
    t = Thread(target=lambda: app.run(port=8083, debug=False, use_reloader=False))
    t.daemon = True; t.start()
    webview.create_window('Reader V10', 'http://127.0.0.1:8083', width=1200, height=900)
    webview.start()
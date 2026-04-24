**Reader V10** is a sleek, distraction-free desktop application designed for reading EPUB books. It combines the flexibility of modern web rendering (Flask, HTML, CSS, JavaScript) with the convenience of a standalone desktop application interface using **pywebview**. The application features an aesthetic "sepia paper" theme, optimized for reading comfort.

The core philosophy is simplicity and functionality: a minimalist library manager paired with a multi-column, paginated reader interface.

---

## ✨ Key Features & Implementation Details

Here is a breakdown of what have been implemented in this version:

### 📖 1. Advanced Reading Interface (Multi-Column Pagination)
Implemented a web-based rendering engine within a native window to gain full control over typography and layout.

* **Paginated CSS Columns:** Instead of traditional vertical scrolling, the books are rendered using CSS3 Multiple Columns. This simulates a classic book experience where the content flows from left to right, divided into pseudo-pages. JavaScript dynamically calculates the total page count based on the content width.
* **Dynamic Font Scaling:** Users can adjust the font size dynamically using the `A+` and `A-` buttons.
    * *Implementation Note:* To maintain the user’s reading context when resizing, the application calculates the current reading progress percentage *before* resizing, then repositions the scroll *after* the resize to match that same percentage.

### 🖼️ 2. Comprehensive Media Support (EPUB Internal Routing)
EPUB files are essentially zipped websites. Implemented internal routing within the Flask backend to handle assets seamlessly.

* **Image Proxying (`/img_proxy`):** EPUBs use relative paths for images internally. The Flask backend includes an `/img_proxy/` route that extracts required images directly from the EPUB archive on-the-fly and serves them to the viewer.
* **Library Book Covers:** The app automatically scans EPUB files for images containing "cover" in their filename. These are extracted, optimized, and converted to `.webp` for efficient loading in the main library grid view.

### 💬 3. Smart Footnotes & Annotations
One of the most complex features of EPUB rendering is handling internal links (footnotes) gracefully.

* **Implementation:** The background service pre-scans the EPUB document to build an ID map of potential footnotes (paragraphs containing a unique ID).
* **Non-Disruptive UX:** In the viewer, hovering over a footnote link (e.g., `[1]`) creates a seamless, stylized tooltip containing the footnote text. This allows the user to check the annotation without jumping away from the current page.

Here is a visual representation of how this tooltip system is realized within the reader interface:

<img width="1408" height="768" alt="image_0" src="https://github.com/user-attachments/assets/754c8c3d-89a8-4336-aad1-8562b070324c" />
# 📚 Reader V10: Lightweight Desktop EPUB Reader

### 📥 4. Library Management & Integrated Downloader
* **Automatic Scanning:** The application scans a local `library` folder for `.epub` files on startup.
* **Metadata Extraction:** It reads `DC:Title` and `DC:Creator` metadata tags directly from the EPUB files to display accurate book titles and author names in the main shelf view.
* **Flibusta Integration:** A simple, direct downloader feature allows you to fetch new books. By inputting a book ID from the Flibusta library, the backend fetches the EPUB file via HTTP and saves it directly to your library folder.

### 💾 5. Progress Saving & Resuming
The app automatically saves your progress per book. It tracks both the current chapter (part) and the specific column (page) you are reading.

* **User Interface:** Upon opening a book, a dedicated modal prompt asks if you wish to "Resume Reading" where you left off or "Start Over" from the beginning. This data is stored using the browser's `localStorage` via the pywebview interface.

---

## ⚙️ Tech Stack

* **Language:** Python 3.x
* **Backend Framework:** Flask (serves HTML, processes metadata, proxies images)
* **GUI Wrapper:** pywebview (renders the interface in a native window)
* **EPUB Parsing:** `ebooklib` & `BeautifulSoup4`
* **Image Handling:** `Pillow` (PIL)

## 🛠️ How to Run

1.  Clone the repository.
2.  Install the requirements:
    ```bash
    pip install Flask ebooklib beautifulsoup4 Pillow pywebview requests
    ```
3.  Add your `.epub` files to the `library` folder that will be created automatically, or use the in-app downloader.
4.  Run the application:
    ```bash
    python reader.py
    ```

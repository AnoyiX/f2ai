import os
import subprocess
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from faster_whisper import WhisperModel

CONVERT_DIR = "static/convert"
WHISPER_MODEL = None
WHISPER_MODEL_PATH = os.path.join("models", "faster-whisper-large-v3")


def get_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        model_path = WHISPER_MODEL_PATH if os.path.exists(WHISPER_MODEL_PATH) else "large-v3"
        print(f"Loading Whisper Model from {model_path}...")
        try:
            WHISPER_MODEL = WhisperModel(model_path, device="cpu", compute_type="int8")
        except Exception as e:
            print(f"Error loading Whisper Model: {e}")
            # Fallback to base model if large fails? Or re-raise?
            # Let's try downloading large-v3 if local path failed but we tried to use it?
            # If model_path was the hardcoded path and it failed (unlikely if exists check passed),
            # If it was "large-v3", it might fail due to network.
            if model_path != "large-v3":
                print("Fallback to large-v3 download...")
                WHISPER_MODEL = WhisperModel("large-v3", device="cpu", compute_type="int8")
    return WHISPER_MODEL


def convert_audio_to_text(audio_path: str, language: str = None) -> str:
    try:
        model = get_whisper_model()
        if not model:
            return "Error: Whisper Model not loaded."

        segments, info = model.transcribe(audio_path, beam_size=5, language=language)

        full_text = []
        for segment in segments:
            # print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
            full_text.append(segment.text)

        return "".join(full_text)
    except Exception as e:
        print(f"Error converting Audio to Text: {e}")
        return f"Error: {str(e)}"


def get_convert_dir(md5: str) -> str:
    path = os.path.join(CONVERT_DIR, md5)
    os.makedirs(path, exist_ok=True)
    return path


def is_text_file(filename: str, content_type: str) -> bool:
    # Basic check for text extensions
    text_exts = ['.txt', '.md', '.html', '.css', '.js', '.py', '.json', '.xml', '.yml', '.yaml', '.log', '.csv']
    ext = os.path.splitext(filename)[1].lower()
    if ext in text_exts:
        return True
    if content_type.startswith('text/'):
        return True
    return False


def convert_office_to_pdf(input_path: str, output_dir: str) -> str:
    """
    Convert office document to PDF using LibreOffice.
    Returns the path to the generated PDF.
    """
    # soffice --headless --convert-to pdf --outdir <output_dir> <input_file>
    # Note: On Docker/Linux, soffice should be in PATH
    soffice_cmd = "soffice"

    cmd = [
        soffice_cmd,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        input_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # The output filename will be same as input but with .pdf extension
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, base_name + ".pdf")

        # Rename to result.pdf as per requirement
        final_pdf_path = os.path.join(output_dir, "result.pdf")
        if os.path.exists(pdf_path):
            if os.path.exists(final_pdf_path):
                os.remove(final_pdf_path)
            os.rename(pdf_path, final_pdf_path)
            return final_pdf_path
        return ""
    except Exception as e:
        print(f"Error converting to PDF: {e}")
        return ""


def convert_pdf_to_images(pdf_path: str, output_dir: str, max_width: int = None, max_height: int = None) -> List[str]:
    """
    Convert PDF to images using pdf2image.
    Returns list of image URLs.
    """
    try:
        # On Docker/Linux, poppler tools (pdftoppm) are in /usr/bin or /usr/local/bin, which are in PATH.
        # So we don't need to specify poppler_path explicitly if it's in PATH.
        images = convert_from_path(pdf_path)
        image_urls = []
        for i, image in enumerate(images):
            image_filename = f"{i+1}.jpg"
            image_path = os.path.join(output_dir, image_filename)
            image.save(image_path, "JPEG")

            # Resize if dimensions provided
            if max_width and max_height:
                try:
                    # Use ImageMagick to resize
                    # Syntax: convert input.jpg -resize "WxH>" output.jpg
                    # > means: only shrink if larger than dimensions
                    resize_arg = f"{max_width}x{max_height}>"
                    cmd = ["convert", image_path, "-resize", resize_arg, image_path]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception as e:
                    print(f"Error resizing image {image_path}: {e}")

            # Construct URL (assuming static mount at root)
            image_urls.append(f"/{output_dir}/{image_filename}")
        return image_urls
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []


def read_text_content(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            return "Unable to decode text content."


def convert_excel_to_html(input_path: str, output_dir: str) -> str:
    """
    Convert Excel file to HTML using LibreOffice (soffice).
    Returns the HTML content string.
    """
    # soffice --headless --convert-to html --outdir <output_dir> <input_file>
    soffice_cmd = "soffice"

    cmd = [
        soffice_cmd,
        "--headless",
        "--convert-to",
        "html",
        "--outdir",
        output_dir,
        input_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # The output filename will be same as input but with .html extension
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        html_path = os.path.join(output_dir, base_name + ".html")

        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean HTML using BeautifulSoup
            try:
                soup = BeautifulSoup(content, 'html.parser')

                # Remove non-content tags
                for tag in soup(['style', 'script', 'meta', 'link', 'title', 'head']):
                    tag.decompose()

                # Remove attributes from all tags, except rowspan and colspan
                for tag in soup.find_all(True):
                    attrs = dict(tag.attrs)
                    for attr in attrs:
                        if attr not in ['rowspan', 'colspan']:
                            del tag[attr]

                # Return cleaned HTML (body content if available)
                if soup.body:
                    # Return only the inner HTML of body to avoid <html><body> tags
                    return "".join([str(x) for x in soup.body.contents])
                return str(soup)
            except Exception as e:
                print(f"Error cleaning HTML: {e}")
                # Fallback to original content if cleaning fails
                return content

        return "Conversion failed: Output file not found."
    except Exception as e:
        print(f"Error converting Excel to HTML: {e}")
        return f"Error converting Excel file: {str(e)}"


def convert_video_to_images(video_path: str, output_dir: str, interval: float = 1.0, max_width: int = None, max_height: int = None) -> List[str]:
    """
    Convert Video to images using ffmpeg.
    Returns list of image URLs.
    """
    try:
        # ffmpeg -i input.mp4 -vf "fps=1/interval,scale=w:h" output_%03d.jpg

        vf_filters = []
        if interval > 0:
            vf_filters.append(f"fps=1/{interval}")

        if max_width and max_height:
            # Scale while keeping aspect ratio, fit within box
            # force_original_aspect_ratio=decrease ensures it fits inside the box
            vf_filters.append(f"scale='min({max_width},iw)':'min({max_height},ih)':force_original_aspect_ratio=decrease")

        vf_arg = ",".join(vf_filters)

        output_pattern = os.path.join(output_dir, "frame_%03d.jpg")

        # Clean up existing frames in output_dir if any?
        # Actually output_dir is per file (md5), so it should be fine.

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", vf_arg,
            "-q:v", "2",  # High quality
            output_pattern
        ]

        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Collect generated images
        image_urls = []
        # Sort files to ensure order
        files = sorted([f for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".jpg")])
        for f in files:
            image_urls.append(f"/{output_dir}/{f}")

        return image_urls
    except Exception as e:
        print(f"Error converting Video to images: {e}")
        return []


def process_file(file_info: Dict[str, Any], image_width: int = None, image_height: int = None, enbaleV2I: bool = True, videoFPS: float = 1.0, enableA2T: bool = True, audioLanguage: str = None) -> Dict[str, Any]:
    file_path = file_info['path']
    filename = file_info['name']
    md5 = file_info['md5']
    content_type = file_info['contentType']

    convert_dir = get_convert_dir(md5)

    result = {
        "text": None,
        "images": [],
        "pdf": None,
        "video": None,
        "audio": None
    }

    ext = os.path.splitext(filename)[1].lower()

    # 1. Doc/Docx/PPT/PPTX
    if ext in ['.doc', '.docx', '.ppt', '.pptx']:
        pdf_path = convert_office_to_pdf(file_path, convert_dir)
        if pdf_path and os.path.exists(pdf_path):
            result["pdf"] = f"/{convert_dir}/result.pdf"
            # Convert PDF to images
            result["images"] = convert_pdf_to_images(pdf_path, convert_dir, image_width, image_height)

    # 2. PDF
    elif ext == '.pdf':
        # Use original upload path, no need to copy
        result["pdf"] = file_info['url']
        result["images"] = convert_pdf_to_images(file_path, convert_dir, image_width, image_height)

    # 3. Excel
    elif ext in ['.xls', '.xlsx']:
        result["text"] = convert_excel_to_html(file_path, convert_dir)

    # 4. Video/Audio
    elif content_type.startswith('video/'):
        result["video"] = file_info['url']
        if enbaleV2I:
            result["images"] = convert_video_to_images(file_path, convert_dir, videoFPS, image_width, image_height)

        # Video to Text? (Not requested, but useful. User asked "Audio files processing", but video also has audio)
        # Requirement: "Increase processing for uploaded audio files... convert audio file to Text"
        # I'll stick to audio files for now unless video/ also needs it.
        # But usually user might want audio from video too.
        # However, strictly speaking, type is 'audio/'.
        # I'll leave video alone for A2T unless I extract audio.

    elif content_type.startswith('audio/'):
        result["audio"] = file_info['url']
        if enableA2T:
            result["text"] = convert_audio_to_text(file_path, audioLanguage)

    # 5. Text/Code
    elif is_text_file(filename, content_type):
        result["text"] = read_text_content(file_path)

    return result

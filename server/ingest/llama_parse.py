import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud_services import LlamaParse


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

# This file is:
# server/ingest/llama_parse.py
#
# parent      -> server/ingest
# parent      -> server
SERVER_ROOT = Path(__file__).resolve().parent.parent

# Load:
# server/.env.local
load_dotenv(SERVER_ROOT / ".env.local")


# ============================================================
# API KEY
# ============================================================

API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "LLAMA_CLOUD_API_KEY is missing.\n"
        "Add it to server/.env.local like:\n\n"
        "LLAMA_CLOUD_API_KEY=your_api_key_here"
    )


# ============================================================
# LLAMAPARSE CLIENT
# ============================================================

parser = LlamaParse(
    api_key=API_KEY,
    result_type="markdown",
)


# ============================================================
# PARSE DOCUMENT
# ============================================================

def parse_document(file_path: str) -> str:
    """
    Parse a shipping document using LlamaParse.

    Args:
        file_path:
            Path to a PDF, DOCX, or other supported document.

    Returns:
        Extracted document text as Markdown.

    Raises:
        FileNotFoundError:
            If the supplied file does not exist.

        ValueError:
            If LlamaParse returns no usable text.
    """

    path = Path(file_path)

    # --------------------------------------------------------
    # Check that file exists
    # --------------------------------------------------------

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {path}"
        )

    print(f"Parsing document: {path}")

    # --------------------------------------------------------
    # Send document to LlamaParse
    # --------------------------------------------------------

    documents = parser.load_data(str(path))

    if not documents:
        raise ValueError(
            f"LlamaParse returned no documents for: {path}"
        )

    # --------------------------------------------------------
    # Combine extracted pages/documents
    # --------------------------------------------------------

    extracted_parts = []

    for document in documents:

        text = getattr(document, "text", None)

        if text:
            extracted_parts.append(text)

    # --------------------------------------------------------
    # Make sure we actually extracted something
    # --------------------------------------------------------

    if not extracted_parts:
        raise ValueError(
            f"LlamaParse returned documents but no text "
            f"was extracted from: {path}"
        )

    text = "\n\n".join(extracted_parts).strip()

    if not text:
        raise ValueError(
            f"LlamaParse returned empty text for: {path}"
        )

    return text


# ============================================================
# SAFE PARSE WRAPPER
# ============================================================

def try_parse_document(file_path: str) -> dict:
    """
    Parse a document without crashing the application.

    This is useful for the eventual fallback pipeline:

        LlamaParse
             |
        success? ---- yes ---> continue
             |
             no
             |
          Gemini fallback

    Returns:

        {
            "success": True,
            "text": "...",
            "error": None
        }

    or:

        {
            "success": False,
            "text": None,
            "error": "..."
        }
    """

    try:

        text = parse_document(file_path)

        return {
            "success": True,
            "text": text,
            "error": None,
        }

    except Exception as e:

        return {
            "success": False,
            "text": None,
            "error": str(e),
        }


# ============================================================
# COMMAND LINE TEST
# ============================================================

def main():
    """
    Allow the parser to be tested directly from PowerShell.

    Example:

        python .\server\ingest\llama_parse.py ".\data_v2\attachments\file.pdf"
    """

    # --------------------------------------------------------
    # Check command-line arguments
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print()
        print("Usage:")
        print(
            '  python .\\server\\ingest\\llama_parse.py "<file>"'
        )
        print()
        print("Example:")
        print(
            '  python .\\server\\ingest\\llama_parse.py '
            '".\\data_v2\\attachments\\example.pdf"'
        )
        print()

        sys.exit(1)

    file_path = sys.argv[1]

    # --------------------------------------------------------
    # Parse document
    # --------------------------------------------------------

    result = try_parse_document(file_path)

    # --------------------------------------------------------
    # Handle failure
    # --------------------------------------------------------

    if not result["success"]:

        print()
        print("=" * 80)
        print("LLAMAPARSE FAILED")
        print("=" * 80)
        print()
        print(result["error"])
        print()

        sys.exit(1)

    # --------------------------------------------------------
    # Print successful extraction
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("LLAMAPARSE SUCCESS")
    print("=" * 80)
    print()

    print(result["text"])

    print()
    print("=" * 80)
    print("END OF EXTRACTED DOCUMENT")
    print("=" * 80)
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
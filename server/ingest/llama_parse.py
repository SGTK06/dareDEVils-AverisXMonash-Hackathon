import os
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud_services import LlamaParse


# Load .env from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "LLAMA_CLOUD_API_KEY is missing. "
        "Add it to the .env file in the project root."
    )


parser = LlamaParse(
    api_key=API_KEY,
    result_type="markdown",
)


def parse_document(file_path: str) -> str:
    """
    Parse a shipping document and return its contents as Markdown.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    print(f"Parsing: {path}")

    documents = parser.load_data(str(path))

    if not documents:
        raise ValueError(f"No content extracted from {path}")

    text = "\n\n".join(
        document.text
        for document in documents
        if getattr(document, "text", None)
    )

    if not text.strip():
        raise ValueError(f"Parser returned empty text for {path}")

    return text


if __name__ == "__main__":
    # Change this to a real SI/BL file when testing.
    test_file = PROJECT_ROOT / "attachments" / "example.pdf"

    try:
        text = parse_document(str(test_file))

        print("\n" + "=" * 80)
        print("EXTRACTED DOCUMENT")
        print("=" * 80)
        print(text)

    except Exception as e:
        print(f"\nERROR: {e}")

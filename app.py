"""Local development entry point; Worker sources live under src/."""

import os

from src.app import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)

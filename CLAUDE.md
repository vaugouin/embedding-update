# Claude (Anthropic) integration

Overview

This file describes how to configure and use Anthropic/Claude as an alternative embedding provider for this project. The main `embedding-update.py` script currently uses OpenAI; to switch to Claude you'll provide a Claude API key and adapt the embedding wrapper to call the Anthropic SDK.

Prerequisites

- A valid Anthropic/Claude API key.
- (Optional) Official Anthropic Python SDK installed, e.g. `pip install anthropic` (check Anthropic docs for the exact package name and version).

Configuration

Two ways to provide the Claude API key:

- Environment variable: set `CLAUDE_API_KEY` in your environment or in your `.env` file.
- Project secrets: add `CLAUDE_API_KEY = "..."` to `citizenphilsecrets.py` (or update `citizenphilsecrets.example.py` accordingly).

Example `.env` entry:

CLAUDE_API_KEY=sk-...your-key...

Minimal usage guidance

The exact SDK usage can change; below is a minimal, generic example of how to call Claude from Python and adapt the embedding function used by `embedding-update.py`.

Example (pseudo-code):

```python
import os
# from anthropic import Client  # uncomment if using the official SDK

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

# client = Client(api_key=CLAUDE_API_KEY)

def claude_embed(texts):
    """Return a list of vectors for `texts` using Claude/Anthropic.
    Replace the body with the actual SDK call for embeddings.
    """
    # Example placeholder -- replace with real SDK call
    # response = client.embeddings.create(model="claude-2.1-embeddings", input=texts)
    # return [r['embedding'] for r in response['data']]
    raise NotImplementedError("Replace with Anthropic/Claude embedding call")

# In `embedding-update.py`, replace the OpenAI embedding function wrapper
# with a wrapper that calls `claude_embed` and returns the vector list.
```

Notes and tips

- Check Anthropic's official docs for the correct package name, import, and method signatures for embeddings (the API surface may change).
- Keep an eye on rate limits and model names; adjust batching/truncation code in `embedding-update.py` to match Claude's limits.
- If you prefer using an environment-based approach, ensure your `.env` loader or `citizenphilsecrets.py` is updated before running the script.

Reference

See `README.md` for overall project usage and where to run `embedding-update.py` from the project root.

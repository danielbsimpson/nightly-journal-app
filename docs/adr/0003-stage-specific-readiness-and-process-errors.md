# Keep recording available when processing is degraded

The `/health` contract reports transcription and processing readiness separately and keeps the API responsive when the llama.cpp server is unavailable, so an LLM-server outage does not prevent recording and transcription. `/process` uses a stable error envelope with explicit unavailable, invalid-output, and timeout status codes; this trades an all-or-nothing health signal for continued access to independent MVP stages and a predictable client contract.

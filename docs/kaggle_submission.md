# Kaggle Submission Checklist

This repo is designed to be submitted as a **Kaggle Writeup** (hackathon-style submission), not as a leaderboard CSV.

## Required links

- Video link (<= 3 minutes)
- Public code repository link

## Recommended order

1) Record the video

- Run the demo locally: `python3 demo/gradio_app.py`
- Show a baseline run (fast) and at least one MedGemma run (pre-warm first if needed)
- Upload the video (e.g., unlisted YouTube) and copy the URL

2) Prepare the writeup content

- Edit `docs/kaggle_writeup.md`
  - Replace the video placeholder with your video URL
  - Confirm the code URL points to the correct branch or commit

3) Submit on Kaggle

- Join the hackathon on the competition page
- Go to the `Writeups` tab -> `New Writeup`
- Paste the contents of `docs/kaggle_writeup.md`
- Select the special award: **Agentic Workflow Prize**
- Submit

## Notes

- `baseline` mode is fully reproducible (no model weights required).
- `medgemma` mode requires gated weights + a Hugging Face token (see `README.md`).

# Synthetic PDFs for NormClaim demos

Generate the four PDFs (including `discharge_complex.pdf` with Hinglish + “No h/o TB”) from the repo root:

```bash
pip install reportlab
python test-data/generate.py
```

Outputs are written next to `generate.py`. Use `discharge_complex.pdf` for the Rajesh Kumar under-coding scenario (multiple comorbidities vs bill with J18.9 only).

If PDFs are gitignored locally, they still run fine for demos after generation.

FLEURS Hindi, test split: 91 utterances, 17.0 min, 140 name mentions, context list of 100 names, every recording degraded to phone-line quality (300-3400 Hz, 8 kHz mu-law). Parakh made 16 extra listens.

| System | Names right | List names written but not said | WER |
|---|---|---|---|
| saaras-v4 + its keyword list | 95.7% | 0 | 5.8% |
| Parakh | 94.3% | 1 | 5.6% |
| Parakh on saaras-v3 | 94.3% | 1 | 6.3% |
| Parakh on gpt-transcribe | 93.6% | 1 | 7.3% |
| gpt-transcribe + its keyword list | 92.1% | 0 | 7.5% |
| saaras-v4 | 86.4% | 0 | 6.5% |
| gpt-transcribe | 86.4% | 0 | 8.3% |
| saaras-v3 | 82.1% | 0 | 7.6% |

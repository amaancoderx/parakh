Sound-alike stress test, FLEURS Hindi test split: 91 utterances, 17.0 min, 140 name mentions. Each recording's own names were removed from the list and 119 sound-alikes put in. Parakh made 50 extra listens.

| System | Sound-alikes written | Any list name written but not said | True names still right | WER |
|---|---|---|---|---|
| gpt-transcribe + its keyword list | 0 of 119 | 0 | 92.9% | 6.8% |
| saaras-v4 | 0 of 119 | 0 | 89.3% | 5.8% |
| gpt-transcribe | 0 of 119 | 0 | 87.9% | 7.4% |
| saaras-v3 | 0 of 119 | 0 | 85.0% | 7.4% |
| Parakh | 2 of 119 | 2 | 95.0% | 5.2% |
| saaras-v4 + its keyword list | 9 of 119 | 11 | 86.4% | 6.4% |

Parakh minus gpt-transcribe + its keyword list, sound-alikes written per recording: +0.022 (95% interval +0.000 to +0.055)
Parakh minus saaras-v4 + its keyword list, sound-alikes written per recording: -0.077 (95% interval -0.143 to -0.022)
Parakh minus saaras-v4, sound-alikes written per recording: +0.022 (95% interval +0.000 to +0.055)

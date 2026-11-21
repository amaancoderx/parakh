Sound-alike stress test, FLEURS Hindi test split: 91 utterances, 17.0 min, 140 name mentions. Each recording's own names were removed from the list and 119 sound-alikes put in. Parakh made 35 extra listens.

| System | Sound-alikes written | Any list name written but not said | True names still right | WER |
|---|---|---|---|---|
| saaras-v4 | 0 of 119 | 0 | 89.3% | 5.8% |
| gpt-transcribe + its keyword list | 0 of 119 | 0 | 89.3% | 7.4% |
| gpt-transcribe | 0 of 119 | 0 | 87.9% | 7.4% |
| saaras-v3 | 0 of 119 | 0 | 85.0% | 7.4% |
| Parakh | 6 of 119 | 6 | 88.6% | 5.8% |
| saaras-v4 + its keyword list | 10 of 119 | 12 | 85.0% | 6.6% |

Parakh minus gpt-transcribe + its keyword list, sound-alikes written per recording: +0.066 (95% interval +0.022 to +0.121)
Parakh minus saaras-v4 + its keyword list, sound-alikes written per recording: -0.044 (95% interval -0.121 to +0.022)
Parakh minus saaras-v4, sound-alikes written per recording: +0.066 (95% interval +0.022 to +0.121)

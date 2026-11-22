Sound-alike stress test, FLEURS Hindi fresh split: 189 utterances, 37.9 min, 313 name mentions. Each recording's own names were removed from the list and 251 sound-alikes put in. Parakh made 101 extra listens.

| System | Sound-alikes written | Any list name written but not said | True names still right | WER |
|---|---|---|---|---|
| gpt-transcribe | 0 of 251 | 3 | 90.7% | 7.4% |
| saaras-v3 | 0 of 251 | 4 | 89.1% | 7.0% |
| Parakh | 1 of 251 | 3 | 96.2% | 3.6% |
| saaras-v4 | 1 of 251 | 4 | 91.1% | 4.6% |
| gpt-transcribe + its keyword list | 2 of 251 | 7 | 93.9% | 7.1% |
| saaras-v4 + its keyword list | 35 of 251 | 37 | 83.1% | 5.0% |

Parakh minus gpt-transcribe + its keyword list, sound-alikes written per recording: -0.005 (95% interval -0.026 to +0.011)
Parakh minus saaras-v4 + its keyword list, sound-alikes written per recording: -0.180 (95% interval -0.238 to -0.127)
Parakh minus saaras-v4, sound-alikes written per recording: +0.000 (95% interval +0.000 to +0.000)

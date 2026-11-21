Sound-alike stress test, FLEURS Hindi fresh split: 189 utterances, 37.9 min, 313 name mentions. Each recording's own names were removed from the list and 251 sound-alikes put in. Parakh made 85 extra listens.

| System | Sound-alikes written | Any list name written but not said | True names still right | WER |
|---|---|---|---|---|
| gpt-transcribe | 0 of 251 | 3 | 90.7% | 7.4% |
| saaras-v3 | 0 of 251 | 4 | 89.1% | 7.0% |
| saaras-v4 | 1 of 251 | 4 | 91.1% | 4.6% |
| gpt-transcribe + its keyword list | 2 of 251 | 5 | 91.4% | 7.4% |
| Parakh | 6 of 251 | 10 | 90.4% | 4.7% |
| saaras-v4 + its keyword list | 35 of 251 | 37 | 80.8% | 5.2% |

Parakh minus gpt-transcribe + its keyword list, sound-alikes written per recording: +0.021 (95% interval +0.005 to +0.042)
Parakh minus saaras-v4 + its keyword list, sound-alikes written per recording: -0.153 (95% interval -0.206 to -0.101)
Parakh minus saaras-v4, sound-alikes written per recording: +0.026 (95% interval +0.005 to +0.053)

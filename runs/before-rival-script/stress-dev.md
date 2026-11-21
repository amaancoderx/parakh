Sound-alike stress test, FLEURS Hindi dev split: 20 utterances, 4.1 min, 36 name mentions. Each recording's own names were removed from the list and 27 sound-alikes put in. Parakh made 5 extra listens.

| System | Sound-alikes written | Any list name written but not said | True names still right | WER |
|---|---|---|---|---|
| saaras-v3 | 0 of 27 | 0 | 86.1% | 6.9% |
| gpt-transcribe | 0 of 27 | 0 | 86.1% | 7.6% |
| saaras-v4 | 0 of 27 | 0 | 80.6% | 7.1% |
| Parakh | 0 of 27 | 0 | 80.6% | 7.1% |
| saaras-v4 + its keyword list | 0 of 27 | 0 | 77.8% | 6.9% |
| gpt-transcribe + its keyword list | 1 of 27 | 1 | 86.1% | 8.4% |

Parakh minus gpt-transcribe + its keyword list, sound-alikes written per recording: -0.050 (95% interval -0.150 to +0.000)
Parakh minus saaras-v4 + its keyword list, sound-alikes written per recording: +0.000 (95% interval +0.000 to +0.000)
Parakh minus saaras-v4, sound-alikes written per recording: +0.000 (95% interval +0.000 to +0.000)

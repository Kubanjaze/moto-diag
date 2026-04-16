"""Media diagnostic intelligence — video/audio analysis for hands-free diagnostics.

Mechanic films a bike starting/running/dying → AI analyzes engine sound signature,
visual symptoms (smoke, leaks, vibration), and behavior → suggests diagnostic paths.

Key capabilities:
- Audio spectrogram analysis: identify knock, misfire, valve tick, exhaust leak
- Video frame analysis: smoke color, fluid leaks, gauge readings (via Claude Vision)
- Multimodal fusion: combine audio + video + text symptoms + DTCs
- Comparative analysis: "before vs after" audio baselines
- Real-time audio monitoring via phone microphone
"""

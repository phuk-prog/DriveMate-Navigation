"""Research music-ducking intent; NOT Android audio-focus integration."""
from dataclasses import dataclass

@dataclass(frozen=True)
class AudioFocusIntent:
    focus: str
    action: str
    restore_after_prompt: bool

def guidance_audio_focus(*,navigation_prompt,other_audio_playing,driver_muted,
                         safety_critical=False):
    if not all(type(v) is bool for v in
               (navigation_prompt,other_audio_playing,driver_muted,safety_critical)):
        raise ValueError("Invalid audio policy flag")
    if not navigation_prompt or (driver_muted and not safety_critical):
        return AudioFocusIntent("NONE","DO_NOT_PLAY",False)
    if other_audio_playing:
        return AudioFocusIntent("TRANSIENT_MAY_DUCK","SPEAK_WITH_MUSIC_DUCK",True)
    return AudioFocusIntent("TRANSIENT","SPEAK",False)

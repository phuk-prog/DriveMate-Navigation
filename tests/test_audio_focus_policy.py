import unittest
from engine.audio_focus_policy import guidance_audio_focus
class AudioFocusPolicyTests(unittest.TestCase):
    def test_existing_music_must_duck_not_pause(self):
        x=guidance_audio_focus(navigation_prompt=True,other_audio_playing=True,
                               driver_muted=False)
        self.assertEqual((x.focus,x.action,x.restore_after_prompt),
                         ("TRANSIENT_MAY_DUCK","SPEAK_WITH_MUSIC_DUCK",True))
    def test_plain_navigation_audio(self):
        self.assertEqual(guidance_audio_focus(navigation_prompt=True,
            other_audio_playing=False,driver_muted=False).action,"SPEAK")
    def test_driver_mute_honoured(self):
        self.assertEqual(guidance_audio_focus(navigation_prompt=True,
            other_audio_playing=True,driver_muted=True).action,"DO_NOT_PLAY")
    def test_critical_override_remains_explicit(self):
        self.assertEqual(guidance_audio_focus(navigation_prompt=True,
            other_audio_playing=True,driver_muted=True,safety_critical=True).focus,
            "TRANSIENT_MAY_DUCK")

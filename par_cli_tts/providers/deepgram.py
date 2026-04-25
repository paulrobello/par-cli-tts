"""Deepgram TTS provider implementation.

Uses Deepgram's REST `/v1/speak` endpoint directly via httpx — no SDK dependency.
Voices and models are unified in Deepgram (the `model` query parameter is the
voice, e.g. `aura-2-thalia-en`), so this provider treats `voice` as the model
identifier and ignores any separately-supplied `model` argument unless it is
explicitly different from the default.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from par_cli_tts.console import console
from par_cli_tts.defaults import DEFAULT_DEEPGRAM_VOICE
from par_cli_tts.http_client import create_http_client
from par_cli_tts.providers.base import TTSProvider, Voice
from par_cli_tts.utils import play_audio_bytes

DEEPGRAM_TTS_ENDPOINT = "https://api.deepgram.com/v1/speak"


# (voice_id, speaker_name, language, accent, description)
_DEEPGRAM_VOICES: tuple[tuple[str, str, str, str, str], ...] = (
    # Aura-2 English
    ("aura-2-thalia-en", "Thalia", "en", "American", "Feminine; clear, confident, energetic"),
    ("aura-2-andromeda-en", "Andromeda", "en", "American", "Feminine; casual, expressive, comfortable"),
    ("aura-2-helena-en", "Helena", "en", "American", "Feminine; caring, natural, friendly"),
    ("aura-2-apollo-en", "Apollo", "en", "American", "Masculine; confident, comfortable, casual"),
    ("aura-2-arcas-en", "Arcas", "en", "American", "Masculine; natural, smooth, clear"),
    ("aura-2-aries-en", "Aries", "en", "American", "Masculine; warm, energetic, caring"),
    ("aura-2-amalthea-en", "Amalthea", "en", "Filipino", "Feminine; engaging, natural, cheerful"),
    ("aura-2-asteria-en", "Asteria", "en", "American", "Feminine; clear, confident, knowledgeable"),
    ("aura-2-athena-en", "Athena", "en", "American", "Feminine; calm, smooth, professional"),
    ("aura-2-atlas-en", "Atlas", "en", "American", "Masculine; enthusiastic, confident, friendly"),
    ("aura-2-aurora-en", "Aurora", "en", "American", "Feminine; cheerful, expressive, energetic"),
    ("aura-2-callista-en", "Callista", "en", "American", "Feminine; clear, energetic, professional"),
    ("aura-2-cora-en", "Cora", "en", "American", "Feminine; smooth, melodic, caring"),
    ("aura-2-cordelia-en", "Cordelia", "en", "American", "Feminine; approachable, warm, polite"),
    ("aura-2-delia-en", "Delia", "en", "American", "Feminine; casual, friendly, cheerful"),
    ("aura-2-draco-en", "Draco", "en", "British", "Masculine; warm, approachable, trustworthy"),
    ("aura-2-electra-en", "Electra", "en", "American", "Feminine; professional, engaging, knowledgeable"),
    ("aura-2-harmonia-en", "Harmonia", "en", "American", "Feminine; empathetic, clear, calm"),
    ("aura-2-hera-en", "Hera", "en", "American", "Feminine; smooth, warm, professional"),
    ("aura-2-hermes-en", "Hermes", "en", "American", "Masculine; expressive, engaging, professional"),
    ("aura-2-hyperion-en", "Hyperion", "en", "Australian", "Masculine; caring, warm, empathetic"),
    ("aura-2-iris-en", "Iris", "en", "American", "Feminine; cheerful, positive, approachable"),
    ("aura-2-janus-en", "Janus", "en", "American", "Feminine; Southern, smooth, trustworthy"),
    ("aura-2-juno-en", "Juno", "en", "American", "Feminine; natural, engaging, melodic"),
    ("aura-2-jupiter-en", "Jupiter", "en", "American", "Masculine; expressive, knowledgeable, baritone"),
    ("aura-2-luna-en", "Luna", "en", "American", "Feminine; friendly, natural, engaging"),
    ("aura-2-mars-en", "Mars", "en", "American", "Masculine; smooth, patient, trustworthy"),
    ("aura-2-minerva-en", "Minerva", "en", "American", "Feminine; positive, friendly, natural"),
    ("aura-2-neptune-en", "Neptune", "en", "American", "Masculine; professional, patient, polite"),
    ("aura-2-odysseus-en", "Odysseus", "en", "American", "Masculine; calm, smooth, professional"),
    ("aura-2-ophelia-en", "Ophelia", "en", "American", "Feminine; expressive, enthusiastic, cheerful"),
    ("aura-2-orion-en", "Orion", "en", "American", "Masculine; approachable, comfortable, calm"),
    ("aura-2-orpheus-en", "Orpheus", "en", "American", "Masculine; professional, clear, confident"),
    ("aura-2-pandora-en", "Pandora", "en", "British", "Feminine; smooth, calm, melodic"),
    ("aura-2-phoebe-en", "Phoebe", "en", "American", "Feminine; energetic, warm, casual"),
    ("aura-2-pluto-en", "Pluto", "en", "American", "Masculine; smooth, calm, empathetic"),
    ("aura-2-saturn-en", "Saturn", "en", "American", "Masculine; knowledgeable, confident, baritone"),
    ("aura-2-selene-en", "Selene", "en", "American", "Feminine; expressive, engaging, energetic"),
    ("aura-2-theia-en", "Theia", "en", "Australian", "Feminine; expressive, polite, sincere"),
    ("aura-2-vesta-en", "Vesta", "en", "American", "Feminine; natural, expressive, empathetic"),
    ("aura-2-zeus-en", "Zeus", "en", "American", "Masculine; deep, trustworthy, smooth"),
    # Aura-2 Spanish
    ("aura-2-celeste-es", "Celeste", "es", "Colombian", "Feminine; clear, energetic, positive"),
    ("aura-2-estrella-es", "Estrella", "es", "Mexican", "Feminine; approachable, natural, calm"),
    ("aura-2-nestor-es", "Nestor", "es", "Peninsular", "Masculine; calm, professional, clear"),
    ("aura-2-sirio-es", "Sirio", "es", "Mexican", "Masculine; calm, professional, empathetic"),
    ("aura-2-carina-es", "Carina", "es", "Peninsular", "Feminine; professional, energetic, confident"),
    ("aura-2-alvaro-es", "Alvaro", "es", "Peninsular", "Masculine; calm, professional, knowledgeable"),
    ("aura-2-diana-es", "Diana", "es", "Peninsular", "Feminine; professional, confident, expressive"),
    ("aura-2-aquila-es", "Aquila", "es", "Latin American", "Masculine; expressive, enthusiastic, casual"),
    ("aura-2-selena-es", "Selena", "es", "Latin American", "Feminine; approachable, casual, friendly"),
    ("aura-2-javier-es", "Javier", "es", "Mexican", "Masculine; approachable, professional, friendly"),
    ("aura-2-agustina-es", "Agustina", "es", "Peninsular", "Feminine; calm, clear, expressive"),
    ("aura-2-antonia-es", "Antonia", "es", "Argentine", "Feminine; approachable, enthusiastic, friendly"),
    ("aura-2-gloria-es", "Gloria", "es", "Colombian", "Feminine; casual, clear, expressive"),
    ("aura-2-luciano-es", "Luciano", "es", "Mexican", "Masculine; charismatic, cheerful, energetic"),
    ("aura-2-olivia-es", "Olivia", "es", "Mexican", "Feminine; breathy, calm, casual"),
    ("aura-2-silvia-es", "Silvia", "es", "Peninsular", "Feminine; charismatic, clear, expressive"),
    ("aura-2-valerio-es", "Valerio", "es", "Mexican", "Masculine; deep, knowledgeable, professional"),
    # Aura-2 Dutch
    ("aura-2-rhea-nl", "Rhea", "nl", "Dutch", "Feminine; caring, knowledgeable, warm"),
    ("aura-2-sander-nl", "Sander", "nl", "Dutch", "Masculine; calm, clear, professional"),
    ("aura-2-beatrix-nl", "Beatrix", "nl", "Dutch", "Feminine; cheerful, enthusiastic, friendly"),
    ("aura-2-daphne-nl", "Daphne", "nl", "Dutch", "Feminine; calm, clear, confident"),
    ("aura-2-cornelia-nl", "Cornelia", "nl", "Dutch", "Feminine; approachable, friendly, warm"),
    ("aura-2-hestia-nl", "Hestia", "nl", "Dutch", "Feminine; approachable, caring, expressive"),
    ("aura-2-lars-nl", "Lars", "nl", "Dutch", "Masculine; breathy, casual, trustworthy"),
    ("aura-2-roman-nl", "Roman", "nl", "Dutch", "Masculine; calm, casual, natural"),
    ("aura-2-leda-nl", "Leda", "nl", "Dutch", "Feminine; caring, empathetic, friendly"),
    # Aura-2 French
    ("aura-2-agathe-fr", "Agathe", "fr", "French", "Feminine; charismatic, cheerful, friendly"),
    ("aura-2-hector-fr", "Hector", "fr", "French", "Masculine; confident, empathetic, friendly"),
    # Aura-2 German
    ("aura-2-julius-de", "Julius", "de", "German", "Masculine; casual, cheerful, engaging"),
    ("aura-2-viktoria-de", "Viktoria", "de", "German", "Feminine; charismatic, enthusiastic, warm"),
    ("aura-2-elara-de", "Elara", "de", "German", "Feminine; calm, clear, natural"),
    ("aura-2-aurelia-de", "Aurelia", "de", "German", "Feminine; approachable, casual, natural"),
    ("aura-2-lara-de", "Lara", "de", "German", "Feminine; caring, cheerful, warm"),
    ("aura-2-fabian-de", "Fabian", "de", "German", "Masculine; confident, knowledgeable, professional"),
    ("aura-2-kara-de", "Kara", "de", "German", "Feminine; caring, empathetic, professional"),
    # Aura-2 Italian
    ("aura-2-livia-it", "Livia", "it", "Italian", "Feminine; approachable, cheerful, engaging"),
    ("aura-2-dionisio-it", "Dionisio", "it", "Italian", "Masculine; confident, engaging, melodic"),
    ("aura-2-melia-it", "Melia", "it", "Italian", "Feminine; clear, comfortable, engaging"),
    ("aura-2-elio-it", "Elio", "it", "Italian", "Masculine; breathy, calm, professional"),
    ("aura-2-flavio-it", "Flavio", "it", "Italian", "Masculine; confident, empathetic, professional"),
    ("aura-2-maia-it", "Maia", "it", "Italian", "Feminine; caring, energetic, professional"),
    ("aura-2-cinzia-it", "Cinzia", "it", "Italian", "Feminine; approachable, friendly, warm"),
    ("aura-2-cesare-it", "Cesare", "it", "Italian", "Masculine; clear, empathetic, natural"),
    ("aura-2-perseo-it", "Perseo", "it", "Italian", "Masculine; casual, clear, polite"),
    ("aura-2-demetra-it", "Demetra", "it", "Italian", "Feminine; calm, comfortable, patient"),
    # Aura-2 Japanese
    ("aura-2-fujin-ja", "Fujin", "ja", "Japanese", "Masculine; calm, confident, knowledgeable"),
    ("aura-2-izanami-ja", "Izanami", "ja", "Japanese", "Feminine; approachable, clear, professional"),
    ("aura-2-uzume-ja", "Uzume", "ja", "Japanese", "Feminine; approachable, clear, professional"),
    ("aura-2-ebisu-ja", "Ebisu", "ja", "Japanese", "Masculine; calm, natural, patient"),
    ("aura-2-ama-ja", "Ama", "ja", "Japanese", "Feminine; casual, comfortable, confident"),
    # Aura-1 English (legacy)
    ("aura-asteria-en", "Asteria (Aura-1)", "en", "American", "Feminine; clear, confident, knowledgeable"),
    ("aura-luna-en", "Luna (Aura-1)", "en", "American", "Feminine; friendly, natural, engaging"),
    ("aura-stella-en", "Stella (Aura-1)", "en", "American", "Feminine; clear, professional, engaging"),
    ("aura-athena-en", "Athena (Aura-1)", "en", "British", "Feminine; calm, smooth, professional"),
    ("aura-hera-en", "Hera (Aura-1)", "en", "American", "Feminine; smooth, warm, professional"),
    ("aura-orion-en", "Orion (Aura-1)", "en", "American", "Masculine; approachable, comfortable, calm"),
    ("aura-arcas-en", "Arcas (Aura-1)", "en", "American", "Masculine; natural, smooth, clear"),
    ("aura-perseus-en", "Perseus (Aura-1)", "en", "American", "Masculine; confident, professional, clear"),
    ("aura-angus-en", "Angus (Aura-1)", "en", "Irish", "Masculine; warm, friendly, natural"),
    ("aura-orpheus-en", "Orpheus (Aura-1)", "en", "American", "Masculine; professional, clear, confident"),
    ("aura-helios-en", "Helios (Aura-1)", "en", "British", "Masculine; professional, clear, confident"),
    ("aura-zeus-en", "Zeus (Aura-1)", "en", "American", "Masculine; deep, trustworthy, smooth"),
)


# Encoding -> (Deepgram `encoding` query value, optional `container` value, file suffix)
_ENCODING_MAP: dict[str, tuple[str, str | None, str]] = {
    "mp3": ("mp3", None, ".mp3"),
    "wav": ("linear16", "wav", ".wav"),
    "flac": ("flac", None, ".flac"),
    "opus": ("opus", "ogg", ".opus"),
    "aac": ("aac", None, ".aac"),
}


class DeepgramProvider(TTSProvider):
    """Deepgram TTS provider (Aura / Aura-2 voices)."""

    VOICE_IDS = frozenset(v[0] for v in _DEEPGRAM_VOICES)

    def __init__(self, api_key: str, **kwargs: Any):
        """Initialize the Deepgram provider.

        Args:
            api_key: Deepgram API key.
            **kwargs: Additional configuration (e.g. `timeout`).
        """
        super().__init__(api_key, **kwargs)
        # Deepgram TTS can take time for long input; use a more generous default.
        self.client = create_http_client(timeout=kwargs.get("timeout", 30.0))

    @property
    def name(self) -> str:
        return "Deepgram"

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3", "wav", "flac", "opus", "aac"]

    @property
    def default_model(self) -> str:
        # Deepgram unifies voice and model: the model IS the voice.
        return DEFAULT_DEEPGRAM_VOICE

    @property
    def default_voice(self) -> str:
        return DEFAULT_DEEPGRAM_VOICE

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        response_format: str = "mp3",
        sample_rate: int | None = None,
        **kwargs: Any,
    ) -> Iterator[bytes]:
        """Stream speech audio chunks for `text` from the Deepgram REST API.

        Args:
            text: Text to convert to speech.
            voice: Deepgram model/voice ID (e.g. `aura-2-thalia-en`).
            model: Optional explicit model override. If supplied and different
                from `voice`, takes precedence — but normally voice is the model.
            response_format: Audio format (mp3, wav, flac, opus, aac).
            sample_rate: Optional sample rate (Hz) — only meaningful for `wav`.
            **kwargs: Ignored.
        """
        del kwargs  # accept but ignore unsupported provider-specific options

        if response_format not in _ENCODING_MAP:
            raise ValueError(
                f"Unsupported Deepgram response_format '{response_format}'. "
                f"Supported: {', '.join(self.supported_formats)}"
            )
        encoding, container, _ = _ENCODING_MAP[response_format]

        active_model = model or voice
        params: dict[str, Any] = {"model": active_model, "encoding": encoding}
        if container:
            params["container"] = container
        if sample_rate is not None:
            params["sample_rate"] = sample_rate

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/*",
        }

        def _stream() -> Iterator[bytes]:
            with self.client.stream(
                "POST",
                DEEPGRAM_TTS_ENDPOINT,
                headers=headers,
                params=params,
                json={"text": text},
            ) as resp:
                if resp.status_code != 200:
                    # Read the (small) error body so the message is useful.
                    body = resp.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"Deepgram API error {resp.status_code}: {body}")
                for chunk in resp.iter_bytes():
                    if chunk:
                        yield chunk

        return _stream()

    def list_voices(self) -> list[Voice]:
        return [
            Voice(
                id=voice_id,
                name=name,
                labels=[lang, accent, *description.split("; ")[1:]],
                category=f"Deepgram {'Aura-2' if voice_id.startswith('aura-2-') else 'Aura-1'} ({lang})",
            )
            for voice_id, name, lang, accent, description in _DEEPGRAM_VOICES
        ]

    def resolve_voice(self, voice_identifier: str) -> str:
        """Resolve a voice name or partial ID to a full Deepgram model ID.

        Accepts:
        - A full ID like ``aura-2-thalia-en`` (returned as-is).
        - A speaker name like ``thalia`` — matches the Aura-2 English voice
          first, then any other Aura-2 voice, then Aura-1.
        - An ID without the trailing ``-en`` like ``aura-2-thalia``.
        """
        ident = voice_identifier.strip().lower()

        # Direct full-ID hit
        if ident in self.VOICE_IDS:
            return ident

        # `aura-2-thalia` -> `aura-2-thalia-en` etc. — match by ID prefix
        prefix_matches = [vid for vid in self.VOICE_IDS if vid.startswith(ident + "-")]
        if len(prefix_matches) == 1:
            console.print(f"[green]✓ Resolved '{voice_identifier}' to voice: {prefix_matches[0]}[/green]")
            return prefix_matches[0]

        # Speaker-name match. Prefer Aura-2 English, then any Aura-2, then Aura-1.
        def _rank(vid: str) -> int:
            if vid.startswith("aura-2-") and vid.endswith("-en"):
                return 0
            if vid.startswith("aura-2-"):
                return 1
            return 2

        name_matches = [vid for (vid, name, *_) in _DEEPGRAM_VOICES if name.lower().split(" ")[0] == ident]
        if name_matches:
            best = sorted(name_matches, key=_rank)[0]
            console.print(f"[green]✓ Resolved '{voice_identifier}' to voice: {best}[/green]")
            return best

        if len(prefix_matches) > 1:
            raise ValueError(f"Voice '{voice_identifier}' is ambiguous. Matches: {', '.join(sorted(prefix_matches))}")

        raise ValueError(f"Voice '{voice_identifier}' not found. Use --list to see available Deepgram voices.")

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(audio_data, bytes):
            path.write_bytes(audio_data)
        else:
            self.stream_to_file(audio_data, path)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        if not isinstance(audio_data, bytes):
            audio_data = b"".join(audio_data)
        # Default container is mp3 unless caller overrode response_format.
        play_audio_bytes(audio_data, volume=volume, suffix=".mp3")

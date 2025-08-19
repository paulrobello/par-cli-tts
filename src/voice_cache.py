"""
Voice cache management for ElevenLabs TTS CLI.

This module handles caching of voice information to improve performance
when translating voice names to IDs.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import platformdirs
import yaml
from elevenlabs.client import ElevenLabs
from rich.console import Console

console = Console()

CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days
CACHE_CHECK_INTERVAL_HOURS = 24  # Check for changes every 24 hours


class VoiceCache:
    """
    Manages cached voice information for faster name-to-ID resolution.

    Uses XDG-compliant directories for storing cache data.
    """

    def __init__(self, app_name: str = "par-tts"):
        """
        Initialize voice cache manager.

        Args:
            app_name: Application name for directory creation.
        """
        self.app_name = app_name
        self.cache_dir = Path(platformdirs.user_cache_dir(app_name))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "voice_cache.yaml"
        self.cache_data: dict[str, Any] = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        """
        Load cache from disk.

        Returns:
            Dictionary containing cached voice data.
        """
        if not self.cache_file.exists():
            return {
                "voices": {},
                "timestamp": None,
                "last_check": None,
                "voice_hash": None,
                "samples": {},
            }

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # Ensure all keys exist
                return {
                    "voices": data.get("voices", {}),
                    "timestamp": data.get("timestamp"),
                    "last_check": data.get("last_check"),
                    "voice_hash": data.get("voice_hash"),
                    "samples": data.get("samples", {}),
                }
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load cache: {e}[/yellow]")
            return {
                "voices": {},
                "timestamp": None,
                "last_check": None,
                "voice_hash": None,
                "samples": {},
            }

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.cache_data, f, default_flow_style=False)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save cache: {e}[/yellow]")

    def is_expired(self) -> bool:
        """
        Check if cache has expired.

        Returns:
            True if cache is expired or invalid, False otherwise.
        """
        if not self.cache_data.get("timestamp"):
            return True

        try:
            cache_time = datetime.fromisoformat(self.cache_data["timestamp"])
            return datetime.now() - cache_time > timedelta(days=CACHE_EXPIRY_DAYS)
        except (ValueError, TypeError):
            return True

    def should_check_for_changes(self) -> bool:
        """
        Check if we should verify if the voice list has changed.

        Returns:
            True if we should check for changes, False otherwise.
        """
        if not self.cache_data.get("last_check"):
            return True

        try:
            last_check = datetime.fromisoformat(self.cache_data["last_check"])
            return datetime.now() - last_check > timedelta(hours=CACHE_CHECK_INTERVAL_HOURS)
        except (ValueError, TypeError):
            return True

    def _compute_voice_hash(self, voices: dict) -> str:
        """
        Compute a hash of the voice list to detect changes.

        Args:
            voices: Dictionary of voice data.

        Returns:
            SHA256 hash of the voice data.
        """
        # Sort voices by ID for consistent hashing
        sorted_voices = sorted(voices.items())
        voice_str = json.dumps(sorted_voices, sort_keys=True)
        return hashlib.sha256(voice_str.encode()).hexdigest()

    def get_voice_by_name(self, name: str) -> str | None:
        """
        Get voice ID by name from cache.

        Args:
            name: Voice name to look up (case-insensitive).

        Returns:
            Voice ID if found, None otherwise.
        """
        if self.is_expired():
            return None

        name_lower = name.lower()
        voices = self.cache_data.get("voices", {})

        # Try exact match first
        for voice_id, voice_info in voices.items():
            if voice_info.get("name", "").lower() == name_lower:
                return voice_id

        # Try partial match
        for voice_id, voice_info in voices.items():
            if name_lower in voice_info.get("name", "").lower():
                return voice_id

        return None

    def get_voice_by_id(self, voice_id: str) -> dict[str, Any] | None:
        """
        Get voice information by ID from cache.

        Args:
            voice_id: Voice ID to look up.

        Returns:
            Voice information dictionary if found, None otherwise.
        """
        if self.is_expired():
            return None

        return self.cache_data.get("voices", {}).get(voice_id)

    def update_cache(self, client: ElevenLabs, force: bool = False) -> bool:
        """
        Update cache with fresh voice data from API.

        Args:
            client: ElevenLabs client instance.
            force: Force update even if no changes detected.

        Returns:
            True if cache was updated, False if no changes.
        """
        try:
            console.print("[cyan]Checking for voice updates...[/cyan]")
            voices = client.voices.get_all()

            new_cache = {}
            for voice in voices.voices:
                labels = list(voice.labels.values()) if voice.labels else []
                new_cache[voice.voice_id] = {
                    "name": voice.name,
                    "labels": labels,
                    "category": voice.category if hasattr(voice, "category") else None,
                }

            # Compute hash to detect changes
            new_hash = self._compute_voice_hash(new_cache)
            old_hash = self.cache_data.get("voice_hash")

            # Update last check timestamp
            self.cache_data["last_check"] = datetime.now().isoformat()

            if not force and old_hash == new_hash:
                console.print("[dim]No voice changes detected[/dim]")
                self._save_cache()  # Save updated last_check
                return False

            # Keep existing samples if any
            existing_samples = self.cache_data.get("samples", {})

            self.cache_data = {
                "voices": new_cache,
                "timestamp": datetime.now().isoformat(),
                "last_check": datetime.now().isoformat(),
                "voice_hash": new_hash,
                "samples": existing_samples,
            }
            self._save_cache()
            console.print(f"[green]✓ Voice cache updated with {len(new_cache)} voices[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Error updating voice cache: {e}[/red]")
            return False

    def list_cached_voices(self) -> list[tuple[str, str, list[str]]]:
        """
        Get list of cached voices.

        Returns:
            List of tuples containing (voice_id, name, labels).
        """
        if self.is_expired():
            return []

        voices = []
        for voice_id, voice_info in self.cache_data.get("voices", {}).items():
            voices.append((voice_id, voice_info.get("name", "Unknown"), voice_info.get("labels", [])))

        return sorted(voices, key=lambda x: x[1].lower())

    def clear_cache(self, keep_samples: bool = False) -> None:
        """Clear the voice cache.

        Args:
            keep_samples: If True, keep cached voice samples.
        """
        samples = self.cache_data.get("samples", {}) if keep_samples else {}
        self.cache_data = {
            "voices": {},
            "timestamp": None,
            "last_check": None,
            "voice_hash": None,
            "samples": samples,
        }
        if self.cache_file.exists() and not keep_samples:
            self.cache_file.unlink()
        elif keep_samples:
            self._save_cache()
        console.print("[green]✓ Voice cache cleared[/green]")
        if keep_samples and samples:
            console.print(f"[dim]Kept {len(samples)} voice samples[/dim]")

    def refresh_cache(self, client: ElevenLabs) -> bool:
        """Force refresh the cache even if not expired.

        Args:
            client: ElevenLabs client instance.

        Returns:
            True if cache was updated, False otherwise.
        """
        console.print("[cyan]Force refreshing voice cache...[/cyan]")
        return self.update_cache(client, force=True)

    def cache_voice_sample(self, voice_id: str, sample_text: str, audio_data: bytes) -> None:
        """Cache a voice sample for offline preview.

        Args:
            voice_id: Voice ID.
            sample_text: Text used for the sample.
            audio_data: Audio data bytes.
        """
        try:
            # Store as base64 to be YAML-safe
            import base64

            if "samples" not in self.cache_data:
                self.cache_data["samples"] = {}

            self.cache_data["samples"][voice_id] = {
                "text": sample_text,
                "audio": base64.b64encode(audio_data).decode("utf-8"),
                "timestamp": datetime.now().isoformat(),
            }
            self._save_cache()
            console.print(f"[dim]Cached voice sample for {voice_id}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not cache voice sample: {e}[/yellow]")

    def get_voice_sample(self, voice_id: str) -> tuple[str, bytes] | None:
        """Get cached voice sample.

        Args:
            voice_id: Voice ID.

        Returns:
            Tuple of (sample_text, audio_data) if found, None otherwise.
        """
        try:
            import base64

            sample = self.cache_data.get("samples", {}).get(voice_id)
            if sample:
                audio_data = base64.b64decode(sample["audio"])
                return sample["text"], audio_data
        except Exception:
            pass
        return None


def resolve_voice_identifier(
    identifier: str, client: ElevenLabs, cache: VoiceCache | None = None, update_cache_if_needed: bool = True
) -> str:
    """
    Resolve a voice identifier (name or ID) to a voice ID.

    Args:
        identifier: Voice name or ID to resolve.
        client: ElevenLabs client instance.
        cache: Optional VoiceCache instance.
        update_cache_if_needed: Whether to update cache if expired.

    Returns:
        Resolved voice ID.

    Raises:
        ValueError: If voice cannot be resolved.
    """
    # If it looks like a voice ID (20+ character alphanumeric), return as-is
    if len(identifier) >= 20 and identifier.replace("_", "").isalnum():
        return identifier

    # Try to resolve from cache first
    if cache:
        cached_id = cache.get_voice_by_name(identifier)
        if cached_id and not cache.is_expired():
            console.print(f"[dim]Using cached voice ID for '{identifier}'[/dim]")

            # Check for changes periodically
            if cache.should_check_for_changes():
                cache.update_cache(client, force=False)

            return cached_id

        # Update cache if expired or not found
        if update_cache_if_needed and (cache.is_expired() or not cached_id):
            cache.update_cache(client)
            cached_id = cache.get_voice_by_name(identifier)
            if cached_id:
                return cached_id

    # Fallback to API lookup
    console.print(f"[cyan]Looking up voice '{identifier}'...[/cyan]")
    try:
        voices = client.voices.get_all()
        identifier_lower = identifier.lower()

        # Try exact match first
        for voice in voices.voices:
            if voice.name and voice.name.lower() == identifier_lower:
                console.print(f"[green]✓ Found voice '{voice.name}' (ID: {voice.voice_id})[/green]")

                # Update cache with new data
                if cache and update_cache_if_needed:
                    cache.update_cache(client)

                return voice.voice_id

        # Try partial match
        matches = []
        for voice in voices.voices:
            if voice.name and identifier_lower in voice.name.lower():
                matches.append((voice.voice_id, voice.name))

        if len(matches) == 1:
            voice_id, voice_name = matches[0]
            console.print(f"[green]✓ Found voice '{voice_name}' (ID: {voice_id})[/green]")

            # Update cache with new data
            if cache and update_cache_if_needed:
                cache.update_cache(client)

            return voice_id
        elif len(matches) > 1:
            console.print(f"[yellow]Multiple voices match '{identifier}':[/yellow]")
            for voice_id, voice_name in matches:
                console.print(f"  - {voice_name} (ID: {voice_id})")
            raise ValueError(f"Ambiguous voice name '{identifier}'. Please be more specific or use voice ID.")

    except Exception as e:
        if "Ambiguous" in str(e):
            raise
        console.print(f"[red]Error looking up voice: {e}[/red]")

    raise ValueError(f"Voice '{identifier}' not found. Use --list to see available voices.")

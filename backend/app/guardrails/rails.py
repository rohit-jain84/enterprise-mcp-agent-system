"""
Guardrails wrapper integrating NeMo Guardrails for input validation and output filtering.

Provides async methods to check user input against defined policies and filter
model output before returning to the user. Falls back to pass-through mode
if NeMo Guardrails is not installed or configuration is missing.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# NeMo Guardrails is an optional dependency; the module degrades gracefully.
try:
    from nemoguardrails import LLMRails, RailsConfig

    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    logger.warning("nemoguardrails package not installed. Guardrails will operate in pass-through mode.")

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "config"


class GuardrailsWrapper:
    """Wrapper around NeMo Guardrails providing input/output safety checks.

    Parameters
    ----------
    config_dir : str | Path | None
        Path to the NeMo Guardrails configuration directory containing
        ``config.yml`` and Colang rail files. Defaults to the ``config/``
        directory shipped alongside this module.
    """

    def __init__(self, config_dir: str | Path | None = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
        self._rails: LLMRails | None = None
        self._enabled: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Load NeMo Guardrails configuration and prepare the rails engine.

        If the nemoguardrails package is missing or the config directory does
        not contain a valid ``config.yml``, the wrapper silently switches to
        pass-through mode so that the rest of the application is unaffected.
        """
        if not NEMO_AVAILABLE:
            logger.info("NeMo Guardrails unavailable; pass-through mode enabled.")
            return

        config_file = self._config_dir / "config.yml"
        if not config_file.exists():
            logger.warning(
                "Guardrails config not found at %s; pass-through mode enabled.",
                config_file,
            )
            return

        try:
            config = RailsConfig.from_path(str(self._config_dir))
            self._rails = LLMRails(config)
            self._enabled = True
            logger.info("NeMo Guardrails initialised from %s.", self._config_dir)
        except Exception:
            logger.exception("Failed to initialise NeMo Guardrails; pass-through mode enabled.")
            self._rails = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        """Return whether guardrails are actively enforcing policies."""
        return self._enabled

    # ------------------------------------------------------------------
    # Input checking
    # ------------------------------------------------------------------

    async def check_input(self, message: str) -> tuple[bool, str | None]:
        """Validate a user message against the configured input rails.

        Parameters
        ----------
        message : str
            The raw user message to validate.

        Returns
        -------
        tuple[bool, str | None]
            ``(True, None)`` if the message is allowed, or
            ``(False, rejection_reason)`` if it was blocked by a rail.
        """
        if not self._enabled or self._rails is None:
            return True, None

        try:
            response = await self._rails.generate_async(messages=[{"role": "user", "content": message}])

            # NeMo Guardrails returns a bot response. If a rail triggered, the
            # response typically starts with "I'm sorry" or similar refusal
            # text and the ``output_data`` may include a blocked flag.
            bot_message: str = ""
            if isinstance(response, dict):
                bot_message = response.get("content", "")
            elif isinstance(response, str):
                bot_message = response
            else:
                # Handle list-of-messages format returned by some versions.
                for msg in response:
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        bot_message = msg.get("content", "")
                        break

            # Heuristic: NeMo rails inject a refusal message when input is
            # blocked. We detect known refusal prefixes.
            _REFUSAL_MARKERS = (
                "i'm sorry",
                "i'm not able",
                "i'm not qualified",
                "i'm unable",
                "i'm designed to help",
                "i'm specifically designed",
                "i'm not able to share",
                "i cannot",
                "i can't",
                "sorry, i can't",
                "i am not able",
                "i appreciate your question, but",
                "i've detected personally identifiable",
                "this request is not allowed",
                "attempts to modify",
            )
            lower_msg = bot_message.strip().lower()
            for marker in _REFUSAL_MARKERS:
                if lower_msg.startswith(marker):
                    reason = bot_message.strip()
                    logger.info("Input blocked by guardrails: %s", reason[:200])
                    return False, reason

            return True, None

        except Exception:
            logger.exception("Error during input guardrail check; allowing input.")
            return True, None

    # ------------------------------------------------------------------
    # Output filtering
    # ------------------------------------------------------------------

    async def check_output(self, response: str) -> str:
        """Filter a model response through the configured output rails.

        Parameters
        ----------
        response : str
            The raw model-generated response.

        Returns
        -------
        str
            The (possibly modified) response after output rail processing.
            If guardrails are disabled the original response is returned
            unchanged.
        """
        if not self._enabled or self._rails is None:
            return response

        try:
            result = await self._rails.generate_async(
                messages=[
                    {"role": "user", "content": "(output check)"},
                    {"role": "assistant", "content": response},
                ]
            )

            filtered: str = response
            if isinstance(result, dict):
                filtered = result.get("content", response)
            elif isinstance(result, str):
                filtered = result
            else:
                for msg in result:
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        filtered = msg.get("content", response)
                        break

            if filtered != response:
                logger.info("Output modified by guardrails.")

            return filtered

        except Exception:
            logger.exception("Error during output guardrail check; returning original response.")
            return response

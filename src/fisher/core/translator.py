from typing import Optional

from discord import Locale
from discord.app_commands import (
    TranslationContext,
    TranslationContextLocation,
    Translator,
    locale_str,
)


class Corpus:
    def __init__(self) -> None:
        self._corpus = {location: {} for location in TranslationContextLocation}

    def add_command_name(self, command_name: str, translation: dict[Locale, str]):
        self._corpus[TranslationContextLocation.command_name][command_name] = (
            translation
        )

    def add_command_description(
        self, command_description: str, translation: dict[Locale, str]
    ):
        self._corpus[TranslationContextLocation.command_description][
            command_description
        ] = translation

    def add_group_name(self, group_name: str, translation: dict[Locale, str]):
        self._corpus[TranslationContextLocation.group_name][group_name] = translation

    def add_group_description(
        self, group_description: str, translation: dict[Locale, str]
    ):
        self._corpus[TranslationContextLocation.group_description][
            group_description
        ] = translation

    def add_parameter_name(self, parameter_name: str, translation: dict[Locale, str]):
        self._corpus[TranslationContextLocation.parameter_name][parameter_name] = (
            translation
        )

    def add_parameter_description(
        self, parameter_description: str, translation: dict[Locale, str]
    ):
        self._corpus[TranslationContextLocation.parameter_description][
            parameter_description
        ] = translation

    def add_choice_name(self, choice_name: str, translation: dict[Locale, str]):
        self._corpus[TranslationContextLocation.choice_name][choice_name] = translation

    def add_other(self, other: str, translation: dict[Locale, str]):
        self._corpus[TranslationContextLocation.other][other] = translation

    def items(self):
        return self._corpus.items()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._corpus})"


class FisherTranslator(Translator):
    def __init__(self) -> None:
        super().__init__()
        self._corpus: dict[
            TranslationContextLocation, dict[str, dict[Locale, str]]
        ] = {}

    def update_corpus(self, corpus: Corpus):
        self._check_corpus(corpus)
        for location, command_item in corpus.items():
            if location not in self._corpus:
                self._corpus[location] = {}
            self._corpus[location].update(command_item)

    def _check_corpus(
        self, corpus: dict[TranslationContextLocation, dict[str, dict[Locale, str]]]
    ):
        for location, command_item in corpus.items():
            if location not in TranslationContextLocation:
                raise TypeError(f"Invalid TranslationContextLocation type: {location}")
            for command, locale_item in command_item.items():
                if not isinstance(command, str):
                    raise ValueError(
                        f"Key of the corpus dict must be a [string], not [{type(command)}]"
                    )
                for locale, translation in locale_item.items():
                    if not isinstance(locale, Locale):
                        raise ValueError(
                            f"Unexpected key type [{type(locale)}] in corpus value. Expected [{type(Locale)}]."
                        )
                    if not isinstance(translation, str):
                        raise ValueError(
                            f"Unexpected value type [{type(translation)}] in corpus value. Expected [string]."
                        )

    async def translate(
        self, string: locale_str, locale: Locale, context: TranslationContext
    ) -> Optional[str]:
        if context.location not in self._corpus:
            return None
        if string.message not in self._corpus[context.location]:
            return None
        if locale not in self._corpus[context.location][string.message]:
            return None

        return self._corpus[context.location][string.message][locale]

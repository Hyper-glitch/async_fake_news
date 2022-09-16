import logging
import string
import time
from contextlib import contextmanager

import aiofiles


def _clean_word(word):
    word = word.replace('«', '').replace('»', '').replace('…', '')
    # FIXME какие еще знаки пунктуации часто встречаются ?
    word = word.strip(string.punctuation)
    return word


@contextmanager
def count_runtime(*args, **kwargs):
    start = time.monotonic()
    article_words = split_by_words(*args, **kwargs)
    end = time.monotonic()
    logging.info(f'Анализ закончен за {end - start} сек')
    yield article_words


def split_by_words(morph, text):
    """Учитывает знаки пунктуации, регистр и словоформы, выкидывает предлоги."""
    words = []

    for word in text.split():
        cleaned_word = _clean_word(word)
        normalized_word = morph.parse(cleaned_word)[0].normal_form
        if len(normalized_word) > 2 or normalized_word == 'не':
            words.append(normalized_word)

    return words


def calculate_jaundice_rate(article_words, charged_words):
    """Расчитывает желтушность текста, принимает список "заряженных" слов и ищет их внутри article_words."""

    if not article_words:
        return 0.0

    found_charged_words = [word for word in article_words if word in set(charged_words)]
    score = len(found_charged_words) / len(article_words) * 100
    return round(score, 2)


async def read_charged_words():
    charged_vocabulary = 'charged_dict'
    positive_words_path = f'{charged_vocabulary}/positive_words.txt'
    negative_words_path = f'{charged_vocabulary}/negative_words.txt'

    charged_words = []
    diry_lines = []

    async with aiofiles.open(positive_words_path, mode='r') as positive, \
            aiofiles.open(negative_words_path, mode='r') as negative:
        positive_lines = await positive.readlines()
        negative_lines = await negative.readlines()

    diry_lines.extend(positive_lines + negative_lines)

    for line in diry_lines:
        charged_words.append(line.rstrip('\n'))

    return charged_words

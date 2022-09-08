import asyncio

import aiohttp
import pymorphy2

import adapters
from text_tools import calculate_jaundice_rate, split_by_words, read_charged_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        html = await fetch(session, 'https://inosmi.ru/20220908/polonez-255973070.html')

    morph = pymorphy2.MorphAnalyzer()
    sanitized_text = adapters.SANITIZERS['inosmi_ru'](html, plaintext=True)
    charged_vocabulary = 'charged_dict'
    word_paths = [f'{charged_vocabulary}/positive_words.txt', f'{charged_vocabulary}/negative_words.txt']

    charged_words = read_charged_words(*word_paths)

    article_words = split_by_words(morph, sanitized_text)

    print(f'Рейтинг: {calculate_jaundice_rate(article_words, charged_words)}\nСлов в статье: {len(article_words)}')


asyncio.run(main())

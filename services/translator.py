# from deep_translator import GoogleTranslator
# from deep_translator.exceptions import RequestError
# import time


# def safe_translate(text, target_lang):
#     # 🔒 Safety checks
#     if not text or not isinstance(text, str):
#         return ""

#     chunk_size = 1200
#     translated = ""

#     # Split long text
#     chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

#     for chunk in chunks:
#         try:
#             translator = GoogleTranslator(
#                 source="auto",
#                 target=target_lang
#             )
#             translated_part = translator.translate(chunk)
#             translated += translated_part + " "
#             time.sleep(0.4)

#         except RequestError:
#             # API limit / temporary fail → fallback
#             translated += chunk + " "

#         except Exception as e:
#             print("❌ Translation error:", e)
#             translated += chunk + " "

#     return translated.strip()


# def translate_summary(text, lang):
#     # 🚫 Do not translate empty or failed summaries
#     if not text or "failed" in text.lower():
#         return text
#     if lang== "en":
#         return text
#     # ✅ ALWAYS translate (even for English)
#     return safe_translate(text, lang)


# def translate_full_news(text, lang):
#     if not text:
#         return ""
#     if lang == "en":
#         return text

#     # ✅ ALWAYS translate (even for English)
#     return safe_translate(text, lang)
from deep_translator import GoogleTranslator
from deep_translator.exceptions import RequestError
import time


def safe_translate(text, target_lang):
    # 🔒 Safety checks
    if not text or not isinstance(text, str):
        return ""

    chunk_size = 1200
    translated = ""

    # Split long text
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    for chunk in chunks:
        try:
            translator = GoogleTranslator(
                source="auto",
                target=target_lang
            )
            translated_part = translator.translate(chunk)
            translated += translated_part + " "
            time.sleep(0.4)

        except RequestError:
            # API limit / temporary fail → fallback
            translated += chunk + " "

        except Exception as e:
            print("❌ Translation error:", e)
            translated += chunk + " "

    return translated.strip()


def translate_summary(text, lang):
    # 🚫 Do not translate empty or failed summaries
    if not text or "failed" in text.lower():
        return text
    
    # Only skip if the destination is English and its already mostly letters (rough check to avoid redundant API)
    # But for full accuracy, we'll let Google handle it since it's source="auto"
    return safe_translate(text, lang)


def translate_full_news(text, lang):
    if not text:
        return ""
    
    return safe_translate(text, lang)

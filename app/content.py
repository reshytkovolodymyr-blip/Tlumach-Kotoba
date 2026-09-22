"""
content.py
----------
Увесь текстовий контент, який показується КРІМ основного робочого
екрана (навігація, «Методологія», «Про програму»), винесений сюди
окремо від gui.py — саме так, щоб ці розділи можна було легко
змінити в майбутньому, не торкаючись коду інтерфейсу.

Формат методології — простий текстовий розмітник (не HTML/Markdown):
    "# "  → заголовок розділу (H1)
    "- "  → пункт списку
    порожній рядок → відступ між абзацами
    будь-який інший непорожній рядок → звичайний абзац
Рендериться в gui.py функцією _render_marked_text() у звичайний
tk.Text через теги — без будь-яких нових залежностей.
"""

from __future__ import annotations

NAV_LABELS = {
    "uk": {
        "new_lesson": "Новий урок",
        "my_lessons": "Мої уроки",
        "methodology": "Методологія",
        "about": "Про програму",
        "interface_language": "Мова інтерфейсу",
    },
    "en": {
        "new_lesson": "New Lesson",
        "my_lessons": "My Lessons",
        "methodology": "Methodology",
        "about": "About",
        "interface_language": "Interface language",
    },
}

# Показується користувачу одразу після зміни мови інтерфейсу — оскільки
# застосування відбувається через перезапуск (свідоме рішення, не баг).
RESTART_NOTICE = {
    "uk": "Мову інтерфейсу змінено. Закрийте це вікно і запустіть "
          "програму знову, щоб зміна набула чинності.",
    "en": "Interface language changed. Close this window and start "
          "the program again for the change to take effect.",
}

ABOUT_TITLE = {"uk": "Про програму", "en": "About"}

ABOUT_TEXT = {
    "uk": "Tlumach Kotoba - програма для вивчення іноземної мови.",
    "en": "Tlumach Kotoba - a program for learning foreign languages.",
}

MY_LESSONS_HINT = {
    "uk": "Подвійний клік по уроку — зробити його поточним і перейти "
          "на вкладку «Новий урок». Права кнопка миші — видалити.",
    "en": "Double-click a lesson to make it current and switch to "
          "the \"New Lesson\" tab. Right-click to delete.",
}

JSON_SECTION_TITLE = {
    "uk": "Зберегти або завантажити",
    "en": "Save or load",
}

# Повний переклад статичних написів усього застосунку (кнопки, заголовки
# секцій, підписи полів). Динамічні повідомлення (статуси з підставленими
# назвами уроків, помилки TTS/FFmpeg) НАРАЗІ лишаються тільки українською —
# це свідоме звуження обсягу цього етапу, а не недогляд: таких повідомлень
# десятки, вони розкидані по throw-код-шляхах, і масова заміна без живого
# тестування GUI — це саме той тип ризикованої правки, якої тут уникають.
# Якщо потрібне повне покриття — це окремий, наступний етап.
UI_STRINGS = {
    "uk": {
        "tagline": "Вивчай мову живим шляхом",
        "card1_title": "1. Створи свій урок",
        "card2_title": "2. Голоси спікерів (обов'язково вручну)",
        "card3_title": "3. Налаштування озвучення",
        "card4_title": "4. Плеєр",
        "no_dialog_hint": "  Не маєте діалогу? Майстер згенерує промпт для AI.",
        "voice_hint": "Стать за іменем ми не вгадуємо — будь ласка, оберіть голос "
                      "для кожного спікера, щоб можна було створити MP3.",
        "voice_empty_hint": "(спершу розберіть діалог)",
        "label_title": "Назва уроку:",
        "label_language": "Мова вивчення:",
        "label_level": "Рівень:",
        "label_rate": "Темп:",
        "label_pause": "Пауза між репліками (сек):",
        "pause_sec_suffix": "сек",
        "pause_recommendation": "рекомендовано 2с",
        "label_mode": "Режим:",
        "btn_new_prompt": "🎯 Новий промпт",
        "btn_paste": "📋 Вставити з буфера",
        "btn_parse": "Розібрати новий діалог",
        "btn_example": "Приклад уроку",
        "btn_clear": "Очистити",
        "btn_create_mp3": "🔊 Створити MP3",
        "btn_export_json": "💾 Export Lesson JSON",
        "btn_import_json": "📂 Import Lesson JSON",
        "btn_open_folder": "📁 Папка MP3",
        "btn_clear_history": "🗑 Очистити всю історію",
        "preview_title": "Прев'ю поточного уроку",
        "history_title": "Історія уроків",
        "mode_full_dialogue": "Full Dialogue",
        "mode_shadowing": "Shadowing (3 проходи)",
        "mode_phrases": "Ключові фрази",
        "mode_recall": "Recall",
        "player_no_file": "Немає завантаженого файлу",
        "player_play": "▶ Play",
        "player_pause": "⏸ Pause",
        "player_stop": "⏹ Stop",
        "player_open": "🎵 Відкрити файл",
        "ok": "OK",
    },
    "en": {
        "tagline": "Learn a language the living way",
        "card1_title": "1. Create your lesson",
        "card2_title": "2. Speaker voices (manual only)",
        "card3_title": "3. Voice settings",
        "card4_title": "4. Player",
        "no_dialog_hint": "  Don't have a dialogue yet? The wizard will generate a prompt for AI.",
        "voice_hint": "We don't guess gender from a name — please choose a voice "
                      "for each speaker so the MP3 can be created.",
        "voice_empty_hint": "(parse a dialogue first)",
        "label_title": "Lesson title:",
        "label_language": "Target language:",
        "label_level": "Level:",
        "label_rate": "Rate:",
        "label_pause": "Pause between lines (sec):",
        "pause_sec_suffix": "sec",
        "pause_recommendation": "recommended: 2s",
        "label_mode": "Mode:",
        "btn_new_prompt": "🎯 New prompt",
        "btn_paste": "📋 Paste from clipboard",
        "btn_parse": "Parse new dialogue",
        "btn_example": "Example lesson",
        "btn_clear": "Clear",
        "btn_create_mp3": "🔊 Create MP3",
        "btn_export_json": "💾 Export Lesson JSON",
        "btn_import_json": "📂 Import Lesson JSON",
        "btn_open_folder": "📁 MP3 folder",
        "btn_clear_history": "🗑 Clear all history",
        "preview_title": "Current lesson preview",
        "history_title": "Lesson history",
        "mode_full_dialogue": "Full Dialogue",
        "mode_shadowing": "Shadowing (3 passes)",
        "mode_phrases": "Key Phrases",
        "mode_recall": "Recall",
        "player_no_file": "No file loaded",
        "player_play": "▶ Play",
        "player_pause": "⏸ Pause",
        "player_stop": "⏹ Stop",
        "player_open": "🎵 Open file",
        "ok": "OK",
    },
}

# Написи стартового майстра промпту (wizard.py) — окремий, менший
# словник, бо майстер і головне вікно живуть у різних класах.
# Динамічні повідомлення (статуси, попередження, підтвердження) — 32
# ключі, кожен з опційними {іменованими} місцями для підстановки через
# .format(). НЕ перекладено (лишається українською в обох мовах):
# повідомлення від AudioError/TTSError (app/audio.py, app/tts.py) —
# "FFmpeg не знайдено", "Не вдалося підключитися до TTS" тощо. Це
# свідоме звуження: ці рядки народжуються в бізнес-логіці, а не в
# gui.py, і додавання туди мови інтерфейсу означало б розширювати
# i18n на модулі, які досі навмисно нічого не знають про Tkinter чи
# мову показу — окрема, більша задача, а не природне продовження цієї.
MESSAGES = {
    "uk": {
        "ready": "Готово. OpenAI API key не потрібен.",
        "wizard_prompt_ready": "Промпт згенеровано — вставте відповідь AI в поле нижче.",
        "warn_prefix": "Увага: ",
        "warn_no_edge_tts": "edge-tts не встановлено — озвучення недоступне",
        "warn_no_pykakasi": "pykakasi не встановлено — romaji для японської недоступний",
        "warn_no_player": "pygame-ce не встановлено — вбудований плеєр недоступний",
        "clipboard_empty": "Буфер обміну порожній або недоступний.",
        "paste_dialog_text": "Вставте текст діалогу.",
        "no_lines_found": "Не знайдено реплік. Використовуйте формат Speaker: text.",
        "example_not_found": "Файл прикладу не знайдено для мови {lang}.",
        "example_loaded_hint": "Приклад завантажено в редактор. Натисніть «{btn}», "
                                "щоб зробити його поточним уроком.",
        "session_created": "Створено новий CURRENT SESSION: «{title}» (id={id}).",
        "session_loaded_from_history": "Урок «{title}» завантажено з історії й став поточним.",
        "confirm_delete_lesson": "Видалити цей урок з історії? Це незворотно.",
        "confirm_clear_history": "Очистити ВСЮ історію уроків? Цю дію не можна скасувати.",
        "lesson_deleted": "Урок видалено з історії.",
        "history_cleared": "Історію уроків очищено.",
        "no_lesson_yet": "Спочатку створіть або завантажте урок.",
        "confirm_replace_lesson": "У вас є активний урок «{title}».\n\n"
                                   "Створити новий? Попередній урок нікуди не зникне — "
                                   "він лишиться в «Мої уроки».",
        "glued_lines_warning": "Здається, у репліці «{snippet}...» посеред тексту "
                                "трапляється ще одне ім'я «{name}:» — можливо, дві "
                                "репліки випадково злиплися в один рядок без переносу.\n\n"
                                "Перевірте, будь ласка, цей момент у тексті, або "
                                "погляньте на «Приклад уроку», щоб звірити формат.",
        "file_exists_prompt": "Файл «{name}» вже існує.\n\n"
                               "Так — перезаписати його.\n"
                               "Ні — зберегти як новий файл (з іншим іменем).\n"
                               "Скасувати — не створювати аудіо.",
        "missing_voices": "Оберіть голос для кожного спікера перед створенням аудіо:\n\n{names}",
        "missing_voice_error": "Не обрано голос для спікера(ів): {names}",
        "no_phrases_for_mode": "У цьому уроці немає ключових фраз для цього режиму.",
        "creating_mp3": "Створення MP3: {label}…",
        "mp3_ready_status": "MP3 готовий. Натисніть ▶ Play у плеєрі, щоб прослухати.",
        "mp3_error_status": "Помилка створення MP3.",
        "generic_error_status": "Помилка.",
        "mp3_ready_dialog": "MP3 готовий:\n\n{path}",
        "unexpected_error": "Неочікувана помилка: {exc}",
        "open_folder_fallback": "Папка з MP3: {dir}",
        "player_unavailable": "Аудіоплеєр недоступний: не встановлено pygame-ce.",
        "lesson_exported": "Урок експортовано: {path}",
        "json_read_error": "Не вдалося прочитати JSON: {exc}",
        "unknown_language_json": "Невідома мова вивчення в JSON: {lang}",
        "lesson_imported": "Урок імпортовано й став поточним: «{title}».",
    },
    "en": {
        "ready": "Ready. No OpenAI API key needed.",
        "wizard_prompt_ready": "Prompt generated — paste the AI's reply into the field below.",
        "warn_prefix": "Warning: ",
        "warn_no_edge_tts": "edge-tts is not installed — voice synthesis is unavailable",
        "warn_no_pykakasi": "pykakasi is not installed — Japanese romaji is unavailable",
        "warn_no_player": "pygame-ce is not installed — the built-in player is unavailable",
        "clipboard_empty": "The clipboard is empty or unavailable.",
        "paste_dialog_text": "Paste the dialogue text.",
        "no_lines_found": "No dialogue lines found. Use the format Speaker: text.",
        "example_not_found": "No example file found for {lang}.",
        "example_loaded_hint": "Example loaded into the editor. Click \"{btn}\" "
                                "to make it the current lesson.",
        "session_created": "Created a new CURRENT SESSION: \"{title}\" (id={id}).",
        "session_loaded_from_history": "Lesson \"{title}\" loaded from history and is now current.",
        "confirm_delete_lesson": "Delete this lesson from history? This cannot be undone.",
        "confirm_clear_history": "Clear ALL lesson history? This action cannot be undone.",
        "lesson_deleted": "Lesson deleted from history.",
        "history_cleared": "Lesson history cleared.",
        "no_lesson_yet": "First create or load a lesson.",
        "confirm_replace_lesson": "You have an active lesson: \"{title}\".\n\n"
                                   "Create a new one? The previous lesson isn't lost — "
                                   "it stays in \"My Lessons\".",
        "glued_lines_warning": "It looks like the line \"{snippet}...\" has another "
                                "name \"{name}:\" in the middle of it — two lines may "
                                "have accidentally merged into one without a line break.\n\n"
                                "Please double-check that spot in the text, or take a "
                                "look at \"Example lesson\" to compare the format.",
        "file_exists_prompt": "The file \"{name}\" already exists.\n\n"
                               "Yes — overwrite it.\n"
                               "No — save as a new file (different name).\n"
                               "Cancel — don't create the audio.",
        "missing_voices": "Choose a voice for every speaker before creating audio:\n\n{names}",
        "missing_voice_error": "No voice chosen for speaker(s): {names}",
        "no_phrases_for_mode": "This lesson has no key phrases for this mode.",
        "creating_mp3": "Creating MP3: {label}…",
        "mp3_ready_status": "MP3 is ready. Click ▶ Play in the player to listen.",
        "mp3_error_status": "Error creating MP3.",
        "generic_error_status": "Error.",
        "mp3_ready_dialog": "MP3 is ready:\n\n{path}",
        "unexpected_error": "Unexpected error: {exc}",
        "open_folder_fallback": "MP3 folder: {dir}",
        "player_unavailable": "The audio player is unavailable: pygame-ce is not installed.",
        "lesson_exported": "Lesson exported: {path}",
        "json_read_error": "Could not read the JSON file: {exc}",
        "unknown_language_json": "Unknown target language in JSON: {lang}",
        "lesson_imported": "Lesson imported and is now current: \"{title}\".",
    },
}

WIZARD_STRINGS = {
    "uk": {
        "window_title": "Новий урок — створити промпт",
        "heading": "Створіть промпт для AI",
        "intro": "Оберіть мову вивчення, рівень і тему — застосунок згенерує "
                 "текст, який можна вставити в ChatGPT (чи будь-який інший AI-чат). "
                 "Відповідь AI потім вставляється назад у програму.",
        "label_language": "Мова вивчення:",
        "label_level": "Рівень:",
        "label_topic": "Тема діалогу:",
        "btn_generate": "Згенерувати промпт",
        "btn_copy": "📋 Копіювати промпт",
        "btn_next": "Далі",
        "copy_first_generate": "Спершу натисніть «Згенерувати промпт».",
        "copied_ok": "Промпт скопійовано в буфер обміну.",
    },
    "en": {
        "window_title": "New lesson — create a prompt",
        "heading": "Create a prompt for AI",
        "intro": "Choose the target language, level and topic — the app will "
                 "generate text you can paste into ChatGPT (or any other AI chat). "
                 "The AI's reply is then pasted back into the app.",
        "label_language": "Target language:",
        "label_level": "Level:",
        "label_topic": "Dialogue topic:",
        "btn_generate": "Generate prompt",
        "btn_copy": "📋 Copy prompt",
        "btn_next": "Next",
        "copy_first_generate": "First click \"Generate prompt\".",
        "copied_ok": "Prompt copied to clipboard.",
    },
}


METHODOLOGY_TITLE = {"uk": "Наукове обґрунтування методу навчання", "en": "Scientific basis of the learning method"}

METHODOLOGY_TEXT = {
    "uk": """
# 1. Вступ

Цей документ пояснює, на яких дослідних принципах побудовані режими
вправ застосунку, і чому вони структуровані саме так, як
структуровані. Це не новий винайдений метод — це інженерна
реалізація кількох задокументованих у психолінгвістиці технік,
застосованих до діалогу, який користувач сам отримує від AI.

# 2. Педагогічний підхід

В основі — вивчення мови через багаторазове прослуховування й
активне відтворення завершених діалогів, а не через заучування
ізольованих слів чи граматичних правил у відриві від контексту.
Ключові принципи:

- Учень працює з одним конкретним, завершеним діалогом, а не з
  абстрактними реченнями поза контекстом.
- Складність зростає поступово: спершу пасивне слухання, потім
  імітація, потім самостійне відтворення без підказки.

# 3. Чотири режими одного діалогу

Усі режими працюють з тим самим уроком — не з новим набором
випадкових речень щоразу, а з тим самим матеріалом, повторюваним із
різною метою.

**Full Dialogue** — весь діалог у природному темпі. Перше занурення
в загальний ритм і мелодику мови без розбиття на частини.

**Shadowing** — три проходи зі зростаючою складністю:
- прохід 1 (повільно) — уповільнений темп знижує навантаження на
  старті, техніка з тренування синхронних перекладачів (Японія,
  1970-ті), пізніше популяризована для самостійного вивчення мов;
- прохід 2 (природний темп) — той самий принцип синхронного
  повторення, тепер у реальному темпі мовлення;
- прохід 3 (без паузи, "наздоганяючий") — повторення ОДНОЧАСНО з
  диктором, без жодної паузи на обдумування — найближче до
  класичного визначення shadowing.

**Ключові фрази** — окремі важливі фрази з діалогу опрацьовуються у
двох блоках: спершу фраза озвучується, потім повільніше, і лише
після цього — переклад і приклад вживання (форма окремо від
значення); далі — зворотний блок, де звучить лише переклад, і потрібно
самому пригадати фразу мовою вивчення, перш ніж почути правильну
відповідь.

**Recall** — репліка діалогу озвучується, тоді пауза на пригадування,
і лише потім — репліка-відповідь із самого діалогу. Це перевірка не
слів, а логіки розмови: чи вдається здогадатись, як розвинеться діалог
далі. Працює виключно мовою вивчення, без перекладу — це саме тому
відрізняється від блоку активного пригадування в "Ключових фразах".

# 4. Чому саме прогресія складності

Ключове інженерне рішення — Shadowing реалізований не одним
проходом, а трьома зі зростаючою складністю. Це відповідає
загальному дидактичному принципу поступового зменшення підтримки
(scaffolding): учень отримує максимум опори на старті і поступово
переходить до умов, максимально наближених до реального мовлення.
Той самий принцип — від впізнавання до самостійного відтворення —
повторюється і в "Ключових фразах", і в Recall.

# 5. Роль застосунку

Застосунок не є новим методом навчання мов — він автоматизує
застосування вже відомих технік до будь-якого діалогу, який
користувач отримує від AI. Технічну складність (розбір тексту,
синтез мовлення, розрахунок і вставку пауз, збирання одного
цілісного MP3-файлу) бере на себе програма; сам педагогічний
принцип спирається на прийоми з самостійним науковим підґрунтям.

- Переклад ніколи не вигадується. Якщо у вправах з'являється
  переклад чи пояснення, воно озвучується лише коли реально присутнє
  в тексті, отриманому від AI.
""",
    "en": """
# 1. Introduction

This document explains the research principles behind the app's
exercise modes, and why they are structured the way they are (three
Shadowing passes, and so on). This is not a newly invented method —
it is an engineering implementation of several techniques documented
in psycholinguistics, applied to a dialogue the user obtains from an
AI.

# 2. Pedagogical approach

The foundation is learning a language through repeated listening and
active reproduction of complete dialogues, rather than memorizing
isolated words or grammar rules out of context. Key principles:

- The learner works with one specific, complete dialogue, not
  abstract, out-of-context sentences.
- Difficulty increases gradually: passive listening first, then
  imitation, then independent reproduction without a prompt.

# 3. Four modes, one dialogue

All modes work with the same lesson — not a new set of random
sentences each time, but the same material, repeated with a
different purpose.

**Full Dialogue** — the whole dialogue at natural pace. The first
exposure to the overall rhythm and melody of the language without
breaking it into parts.

**Shadowing** — three passes of increasing difficulty:
- pass 1 (slow) — a slower pace reduces load at the start, a
  technique from simultaneous-interpreter training (Japan, 1970s),
  later popularized for self-study;
- pass 2 (natural pace) — the same synchronous-repetition principle,
  now at real speaking speed;
- pass 3 (no pause, "catch-up") — repeating AT THE SAME TIME as the
  speaker, with no pause to think — closest to the classic
  definition of shadowing.

**Key Phrases** — individual important phrases from the dialogue are
practiced in two blocks: first the phrase is spoken, then slower,
and only after that — the translation and an example of use (form
kept separate from meaning); then a reverse block, where only the
translation is spoken, and you must recall the phrase in the target
language yourself before hearing the correct answer.

**Recall** — a line from the dialogue is spoken, then a pause to
recall, and only then the answer line from the dialogue itself. This
tests not vocabulary but the logic of the conversation — can you
guess how the dialogue continues. It works entirely in the target
language, with no translation — which is exactly what sets it apart
from the active-recall block inside Key Phrases.

# 4. Why a progression of difficulty

The key engineering decision is that Shadowing is implemented as
three passes of increasing difficulty rather than one. This follows
the general didactic principle of gradually reducing support
(scaffolding): the learner gets maximum support at the start and
gradually moves toward conditions as close as possible to real
speech. The same principle — from recognition to independent
reproduction — repeats in both Key Phrases and Recall.

# 5. Role of the application

The application is not a new language-learning method — it
automates the application of already-known techniques to any
dialogue the user obtains from an AI. The technical complexity (text
parsing, speech synthesis, pause calculation and insertion, assembling
one continuous MP3 file) is handled by the program; the pedagogical
principle itself relies on techniques with independent scientific
grounding.

- The translation is never invented. If a translation or explanation
  appears in an exercise, it is only spoken when it is actually
  present in the text received from the AI.
""",
}


# ======================================================================
# Редизайн «Новий урок» у три кроки (1 Створи урок → 2 Налаштуй голоси →
# 3 Практикуйся). Окремий блок, щоб не переписувати словники вище:
# нові ключі додаються, а кілька старих написів ПЕРЕВИЗНАЧАЮТЬСЯ на
# коротші, без емодзі (під новий стиль кнопок). Набори ключів uk/en
# мають лишатися ідентичними — це перевіряється після кожної зміни.
# ======================================================================
_UI_STEPS = {
    "uk": {
        "step1_label": "Створи урок",
        "step2_label": "Налаштуй голоси",
        "step3_label": "Практикуйся",
        "s1_title": "Створи свій урок",
        "s1_sub": "Вставте діалог, який згенерував AI. Кожна репліка — з нового рядка.",
        "s1_placeholder": "Emma: Hello!\nJack: Hi, Emma!\n\nhello - привіт",
        "label_dialog": "Діалог",
        "btn_next_voices": "Далі: голоси →",
        "s2_title": "Налаштуй голоси",
        "gender_female": "Жіночий",
        "gender_male": "Чоловічий",
        "btn_back": "← Назад",
        "btn_next_practice": "Далі: практика →",
        "preview_card_title": "Перегляд уроку",
        "preview_phrases": "Ключові фрази",
        "preview_no_phrases": "У цьому уроці немає ключових фраз.",
        "preview_no_translation": "переклад відсутній у тексті уроку",
        "preview_no_romaji": "romaji недоступний",
        "s3_title": "Практикуйся",
        "s3_sub": "Оберіть режим — програма створить один MP3-файл для цього уроку.",
        "mode_shadowing_short": "Shadowing",
        "mode_full_desc": "Весь діалог у природному темпі. Перше знайомство зі звучанням.",
        "mode_shadowing_desc": "Три проходи: повільно, у природному темпі, разом із диктором.",
        "mode_phrases_desc": "Фраза, переклад і приклад — потім пригадати фразу самостійно.",
        "mode_recall_desc": "Репліка, пауза — чи вгадаєте, що відповість співрозмовник?",
        "player_title": "Плеєр",
        "zoom_tooltip": "Масштаб інтерфейсу · Ctrl + / Ctrl − / Ctrl 0",
        "zoom_in": "Збільшити масштаб",
        "zoom_out": "Зменшити масштаб",
        "empty_history": "Поки немає збережених уроків.",
        "btn_first_lesson": "Створити перший урок",
        "about_zoom_hint": "Натисніть на зображення, щоб відкрити його в повному розмірі",
        "menu_delete": "Видалити урок",
        "method_formula": "почув → зрозумів → повторив → прискорив → відтворив самостійно",
        "parse_tooltip": "Ctrl+Enter",
        "create_tooltip": "Ctrl+M",
        # перевизначені (коротші, без емодзі)
        "btn_new_prompt": "Новий промпт",
        "btn_paste": "Вставити з буфера",
        "btn_parse": "Розібрати діалог",
        "btn_create_mp3": "Створити MP3",
        "btn_export_json": "Експорт JSON",
        "btn_import_json": "Імпорт JSON",
        "btn_open_folder": "Папка MP3",
        "btn_clear_history": "Очистити історію",
        "player_open": "Відкрити файл",
        "label_title": "Назва уроку",
        "label_language": "Мова",
        "label_level": "Рівень",
        "label_rate": "Темп мовлення",
        "label_pause": "Пауза між репліками",
        "pause_recommendation": "рекомендовано 2 с",
        "pause_sec_suffix": "с",
    },
    "en": {
        "step1_label": "Create lesson",
        "step2_label": "Set up voices",
        "step3_label": "Practice",
        "s1_title": "Create your lesson",
        "s1_sub": "Paste the dialogue generated by AI. Each line goes on a new row.",
        "s1_placeholder": "Emma: Hello!\nJack: Hi, Emma!\n\nhello - привіт",
        "label_dialog": "Dialogue",
        "btn_next_voices": "Next: voices →",
        "s2_title": "Set up voices",
        "gender_female": "Female",
        "gender_male": "Male",
        "btn_back": "← Back",
        "btn_next_practice": "Next: practice →",
        "preview_card_title": "Lesson preview",
        "preview_phrases": "Key phrases",
        "preview_no_phrases": "This lesson has no key phrases.",
        "preview_no_translation": "no translation in the lesson text",
        "preview_no_romaji": "romaji unavailable",
        "s3_title": "Practice",
        "s3_sub": "Choose a mode — the app creates one MP3 file for this lesson.",
        "mode_shadowing_short": "Shadowing",
        "mode_full_desc": "The whole dialogue at natural pace. A first feel for the sound.",
        "mode_shadowing_desc": "Three passes: slow, natural pace, together with the speaker.",
        "mode_phrases_desc": "Phrase, translation and example — then recall the phrase yourself.",
        "mode_recall_desc": "A line, a pause — can you guess what the other person replies?",
        "player_title": "Player",
        "zoom_tooltip": "Interface zoom · Ctrl + / Ctrl − / Ctrl 0",
        "zoom_in": "Zoom in",
        "zoom_out": "Zoom out",
        "empty_history": "No saved lessons yet.",
        "btn_first_lesson": "Create your first lesson",
        "about_zoom_hint": "Click the image to open it at full size",
        "menu_delete": "Delete lesson",
        "method_formula": "heard → understood → repeated → sped up → reproduced on your own",
        "parse_tooltip": "Ctrl+Enter",
        "create_tooltip": "Ctrl+M",
        "btn_new_prompt": "New prompt",
        "btn_paste": "Paste from clipboard",
        "btn_parse": "Parse dialogue",
        "btn_create_mp3": "Create MP3",
        "btn_export_json": "Export JSON",
        "btn_import_json": "Import JSON",
        "btn_open_folder": "MP3 folder",
        "btn_clear_history": "Clear history",
        "player_open": "Open file",
        "label_title": "Lesson title",
        "label_language": "Language",
        "label_level": "Level",
        "label_rate": "Speech rate",
        "label_pause": "Pause between lines",
        "pause_recommendation": "recommended: 2 s",
        "pause_sec_suffix": "s",
    },
}

_MSG_STEPS = {
    "uk": {
        "parsed_ok": "Розібрано: {lines} · {speakers} · {phrases}.",
        "glued_inline": "Репліка {row}: схоже, дві репліки злиплися — посередині трапляється "
                        "«{name}:». Додайте перенос рядка або порівняйте з прикладом уроку.",
        "voices_missing_inline": "Оберіть голос для: {names} — тоді можна перейти до практики.",
        "voices_ok_inline": "Усі голоси обрано — можна практикуватися.",
        "progress_speaking": "Озвучення {n} з {total}",
        "progress_merging": "Об'єднання в один MP3…",
        "speakers_chip": "Персонажів: {n}",
        "lesson_meta": "{title} · {lang} · {level}",
    },
    "en": {
        "parsed_ok": "Parsed: {lines} · {speakers} · {phrases}.",
        "glued_inline": "Line {row}: two lines seem to have merged — «{name}:» appears in the "
                        "middle. Add a line break or compare with the example lesson.",
        "voices_missing_inline": "Choose a voice for: {names} — then you can move on to practice.",
        "voices_ok_inline": "All voices are set — you can practice now.",
        "progress_speaking": "Voicing {n} of {total}",
        "progress_merging": "Merging into one MP3…",
        "speakers_chip": "Speakers: {n}",
        "lesson_meta": "{title} · {lang} · {level}",
    },
}

for _lang in ("uk", "en"):
    UI_STRINGS[_lang].update(_UI_STEPS[_lang])
    MESSAGES[_lang].update(_MSG_STEPS[_lang])

# Форми множини для лічильників ("1 репліка / 3 репліки / 5 реплік").
# Для української — три форми (правило однини/пари/множини), для
# англійської — дві.
COUNT_FORMS = {
    "uk": {
        "line": ("репліка", "репліки", "реплік"),
        "speaker": ("спікер", "спікери", "спікерів"),
        "phrase": ("ключова фраза", "ключові фрази", "ключових фраз"),
    },
    "en": {
        "line": ("line", "lines"),
        "speaker": ("speaker", "speakers"),
        "phrase": ("key phrase", "key phrases"),
    },
}

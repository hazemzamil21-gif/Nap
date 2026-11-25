import ast
import datetime
import json
import math
import os
import re
import shutil
import threading
import urllib.parse
import urllib.request
from jnius import autoclass, PythonJavaClass, java_method
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, Triangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

PythonActivity = autoclass('org.kivy.android.PythonActivity')
Intent = autoclass('android.content.Intent')
Uri = autoclass('android.net.Uri')
Settings = autoclass('android.provider.Settings')
TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
Locale = autoclass('java.util.Locale')
PackageManager = autoclass('android.content.pm.PackageManager')
Context = autoclass('android.content.Context')
AlarmManager = autoclass('android.app.AlarmManager')
PendingIntent = autoclass('android.app.PendingIntent')
Calendar = autoclass('java.util.Calendar')

REMINDERS_FILE = 'reminders.json'
SNIPPETS_DIR = 'snippets'
FIXED_DIR = 'fixed_output'
PS1_DIR = 'ps1_scripts'
GEN_SCRIPTS_DIR = 'generated_scripts'
JAVA_BUILD_DIR = 'java_apk_build'

OFFLINE_AR_TO_FR_EN = {
    'مرحبا': ('Bonjour', 'Hello'),
    'أهلا': ('Bonjour', 'Hello'),
    'صباح الخير': ('Bonjour', 'Good morning'),
    'مساء الخير': ('Bonsoir', 'Good evening'),
    'شكرا': ('Merci', 'Thank you'),
    'شكرا لك': ('Merci beaucoup', 'Thank you'),
    'نعم': ('Oui', 'Yes'),
    'لا': ('Non', 'No'),
    'من فضلك': ("S'il vous plaît", 'Please'),
    'عفوا': ('De rien', "You're welcome"),
    'أين': ('Où', 'Where'),
    'متى': ('Quand', 'When'),
    'لماذا': ('Pourquoi', 'Why'),
    'كيف حالك': ('Comment ça va ?', 'How are you?'),
    'أنا أتعلم الفرنسية': ("J'apprends le français", 'I am learning French'),
    'إلى اللقاء': ('Au revoir', 'Goodbye'),
}

OFFLINE_FOREIGN_TO_AR = {
    'bonjour': 'مرحباً / صباح الخير',
    'bonsoir': 'مساء الخير',
    'merci': 'شكراً',
    'oui': 'نعم',
    'non': 'لا',
    'au revoir': 'إلى اللقاء',
    'comment ca va': 'كيف حالك؟',
    'comment ça va': 'كيف حالك؟',
    'hello': 'مرحباً',
    'good morning': 'صباح الخير',
    'good evening': 'مساء الخير',
    'thank you': 'شكراً لك',
    'yes': 'نعم',
    'no': 'لا',
    'please': 'من فضلك',
    'goodbye': 'إلى اللقاء',
    'how are you': 'كيف حالك؟',
}

LANGUAGES_DB = {
    'python': ('py', 'def main():\n    print("Hello")\n\nif __name__ == "__main__":\n    main()\n'),
    'javascript': ('js', 'function main() {\n  console.log("Hello");\n}\n\nmain();\n'),
    'typescript': ('ts', 'function main(): void {\n  console.log("Hello");\n}\n\nmain();\n'),
    'java': ('java', 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello");\n    }\n}\n'),
    'kotlin': ('kt', 'fun main() {\n    println("Hello")\n}\n'),
    'c': ('c', '#include <stdio.h>\n\nint main(void) {\n    printf("Hello\\n");\n    return 0;\n}\n'),
    'cpp': ('cpp', '#include <iostream>\n\nint main() {\n    std::cout << "Hello" << std::endl;\n    return 0;\n}\n'),
    'csharp': ('cs', 'using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello");\n    }\n}\n'),
    'go': ('go', 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello")\n}\n'),
    'rust': ('rs', 'fn main() {\n    println!("Hello");\n}\n'),
    'php': ('php', '<?php\necho "Hello\\n";\n'),
    'ruby': ('rb', 'def main\n  puts "Hello"\nend\n\nmain\n'),
    'swift': ('swift', 'import Foundation\n\nprint("Hello")\n'),
    'dart': ('dart', 'void main() {\n  print("Hello");\n}\n'),
    'bash': ('sh', '#!/usr/bin/env bash\nset -euo pipefail\n\necho "Running..."\n'),
    'powershell': ('ps1', 'Write-Host "Running..."\n'),
    'html': ('html', '<!DOCTYPE html>\n<html>\n<head><meta charset="UTF-8"><title>App</title></head>\n<body><h1>Hello</h1></body>\n</html>\n'),
    'css': ('css', 'body {\n  font-family: sans-serif;\n  margin: 0;\n  padding: 16px;\n}\n'),
    'sql': ('sql', 'SELECT id, name FROM users WHERE active = 1;\n'),
    'lua': ('lua', 'local function main()\n  print("Hello")\nend\n\nmain()\n'),
    'kivy': ('py', 'from kivy.app import App\nfrom kivy.uix.label import Label\n\nclass MyApp(App):\n    def build(self):\n        return Label(text="Napoleon")\n\nMyApp().run()\n'),
}

LANG_ALIASES = {
    'بايثون': 'python', 'python': 'python', 'py': 'python',
    'جافا سكريبت': 'javascript', 'جافاسكريبت': 'javascript', 'javascript': 'javascript', 'js': 'javascript',
    'تايب سكريبت': 'typescript', 'تايبسكريبت': 'typescript', 'typescript': 'typescript', 'ts': 'typescript',
    'جافا': 'java', 'java': 'java',
    'كوتلن': 'kotlin', 'kotlin': 'kotlin', 'kt': 'kotlin',
    'سي': 'c', 'c': 'c',
    'سي بلس بلس': 'cpp', 'سي++': 'cpp', 'cpp': 'cpp', 'c++': 'cpp',
    'سي شارب': 'csharp', 'سي#': 'csharp', 'csharp': 'csharp', 'cs': 'csharp',
    'جو': 'go', 'go': 'go', 'golang': 'go',
    'رست': 'rust', 'rust': 'rust', 'rs': 'rust',
    'بي اتش بي': 'php', 'بي إتش بي': 'php', 'php': 'php',
    'روبي': 'ruby', 'ruby': 'ruby', 'rb': 'ruby',
    'سويفت': 'swift', 'swift': 'swift',
    'دارت': 'dart', 'dart': 'dart',
    'باش': 'bash', 'bash': 'bash', 'sh': 'bash',
    'باور شيل': 'powershell', 'باورشيل': 'powershell', 'powershell': 'powershell', 'ps1': 'powershell',
    'اتش تي ام ال': 'html', 'html': 'html',
    'سي اس اس': 'css', 'css': 'css',
    'اس كيو ال': 'sql', 'sql': 'sql',
    'لوا': 'lua', 'lua': 'lua',
    'كيفي': 'kivy', 'kivy': 'kivy',
}


class TTSInitListener(PythonJavaClass):
    __javainterfaces__ = ['android.speech.tts.TextToSpeech$OnInitListener']
    __javacontext__ = 'app'

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    @java_method('(I)V')
    def onInit(self, status):
        if status == TextToSpeech.SUCCESS:
            self.widget.on_tts_ready()


class NapoleonWidget(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.context = PythonActivity.mActivity
        self.tts = None
        self.tts_ready = False
        self.listener = TTSInitListener(self)
        self.reminders = self.load_reminders()
        self.watched_file = None
        self.last_watched_hash = None
        self.last_error_signature = None

        for d in (SNIPPETS_DIR, FIXED_DIR, PS1_DIR, GEN_SCRIPTS_DIR):
            os.makedirs(d, exist_ok=True)

        self.avatar_pos = [110.0, 320.0]
        self.avatar_size = (150.0, 175.0)
        self.bob_offset = 0.0
        self.canvas_items = {}
        self.build_napoleon_canvas()

        self.ui_box = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(520, 270),
            pos=(50, 55),
            spacing=8,
        )

        self.speech_bubble = Label(
            text='ارحب يا شيخ',
            size_hint_y=0.44,
            color=(1, 1, 1, 1),
            halign='center',
        )

        self.cmd_input = TextInput(
            hint_text='سكربت [نوع + وصف] / ps1 [مهمة] / صحح [ملف] / راقب [ملف] / ترجم / عربي',
            multiline=False,
            size_hint_y=0.31,
        )
        self.cmd_input.bind(text=self.on_typing_live_check)

        self.send_btn = Button(
            text='نفّذ الأمر',
            size_hint_y=0.25,
            background_color=(0.10, 0.20, 0.50, 1),
        )
        self.send_btn.bind(on_press=self.process_command)

        self.ui_box.add_widget(self.speech_bubble)
        self.ui_box.add_widget(self.cmd_input)
        self.ui_box.add_widget(self.send_btn)
        self.add_widget(self.ui_box)

        self.init_tts()
        Clock.schedule_interval(self.check_due_reminders, 15)
        Clock.schedule_interval(self.animate_idle, 0.08)
        Clock.schedule_interval(self.watch_code_file_loop, 2.0)

    def build_napoleon_canvas(self):
        with self.canvas.before:
            Color(0.08, 0.16, 0.42, 1)
            self.canvas_items['coat'] = Rectangle(pos=(0, 0), size=(120, 72))

            Color(0.95, 0.95, 0.97, 1)
            self.canvas_items['vest'] = Rectangle(pos=(0, 0), size=(36, 52))

            Color(0.75, 0.12, 0.16, 1)
            self.canvas_items['collar'] = Rectangle(pos=(0, 0), size=(56, 14))

            Color(0.95, 0.78, 0.20, 1)
            self.canvas_items['btn1'] = Ellipse(pos=(0, 0), size=(8, 8))
            self.canvas_items['btn2'] = Ellipse(pos=(0, 0), size=(8, 8))

            Color(0.95, 0.77, 0.63, 1)
            self.canvas_items['face'] = Ellipse(pos=(0, 0), size=(52, 54))

            Color(0.10, 0.10, 0.14, 1)
            self.canvas_items['eye_l'] = Ellipse(pos=(0, 0), size=(7, 7))
            self.canvas_items['eye_r'] = Ellipse(pos=(0, 0), size=(7, 7))

            Color(0.06, 0.08, 0.16, 1)
            self.canvas_items['hat'] = Triangle(points=[0, 0, 1, 0, 0.5, 1])

            Color(0.98, 0.82, 0.22, 1)
            self.canvas_items['cockade'] = Ellipse(pos=(0, 0), size=(12, 12))

        self.update_napoleon_positions()

    def update_napoleon_positions(self):
        x = self.avatar_pos[0]
        y = self.avatar_pos[1] + self.bob_offset

        self.canvas_items['coat'].pos = (x + 15, y)
        self.canvas_items['coat'].size = (120, 72)

        self.canvas_items['vest'].pos = (x + 57, y + 12)
        self.canvas_items['vest'].size = (36, 52)

        self.canvas_items['collar'].pos = (x + 47, y + 66)
        self.canvas_items['collar'].size = (56, 14)

        self.canvas_items['btn1'].pos = (x + 71, y + 42)
        self.canvas_items['btn2'].pos = (x + 71, y + 24)

        self.canvas_items['face'].pos = (x + 49, y + 78)
        self.canvas_items['face'].size = (52, 54)

        self.canvas_items['eye_l'].pos = (x + 60, y + 105)
        self.canvas_items['eye_r'].pos = (x + 83, y + 105)

        self.canvas_items['hat'].points = [
            x + 5, y + 128,
            x + 145, y + 128,
            x + 75, y + 172,
        ]

        self.canvas_items['cockade'].pos = (x + 69, y + 134)

    def animate_idle(self, dt):
        self.bob_offset = math.sin(Clock.get_boottime() * 2.5) * 4.0
        self.update_napoleon_positions()

    def init_tts(self):
        self.tts = TextToSpeech(self.context, self.listener)

    def on_tts_ready(self):
        self.tts_ready = True
        self.tts.setLanguage(Locale('ar'))
        self.tts.setPitch(0.62)
        self.tts.setSpeechRate(0.85)
        Clock.schedule_once(lambda dt: self.speak('ارحب يا شيخ'), 0.4)

    def speak(self, text, lang_code='ar', queue_mode=TextToSpeech.QUEUE_FLUSH):
        if lang_code == 'ar':
            self.speech_bubble.text = text
        if self.tts and self.tts_ready:
            if lang_code == 'fr':
                self.tts.setLanguage(Locale.FRENCH)
                self.tts.setPitch(0.85)
                self.tts.setSpeechRate(0.88)
            elif lang_code == 'en':
                self.tts.setLanguage(Locale.ENGLISH)
                self.tts.setPitch(0.82)
                self.tts.setSpeechRate(0.90)
            else:
                self.tts.setLanguage(Locale('ar'))
                self.tts.setPitch(0.62)
                self.tts.setSpeechRate(0.85)
            self.tts.speak(text, queue_mode, None, None)

    def on_touch_move(self, touch):
        x, y = self.avatar_pos
        w, h = self.avatar_size
        if x <= touch.x <= x + w and y <= touch.y <= y + h + 40:
            self.avatar_pos = [touch.x - w / 2, touch.y - h / 2]
            self.update_napoleon_positions()
            self.ui_box.pos = (touch.x - 220, touch.y - 270)
        return super().on_touch_move(touch)

    def generate_any_script(self, raw_desc):
        parts = raw_desc.strip().split(maxsplit=1)
        first_token = parts[0].lower() if parts else ''
        canonical_lang = LANG_ALIASES.get(first_token)

        if canonical_lang and canonical_lang in LANGUAGES_DB:
            ext, _ = LANGUAGES_DB[canonical_lang]
            lang_label = canonical_lang
            desc = parts[1].strip() if len(parts) > 1 else f'{canonical_lang} script'
        else:
            ext = 'sh'
            lang_label = 'script'
            desc = raw_desc.strip() or 'custom script'

        safe_slug = re.sub(r'[^\w\-]+', '_', desc.lower()).strip('_')[:36] or 'script'
        out_path = os.path.join(GEN_SCRIPTS_DIR, f'{safe_slug}.{ext}')

        if ext == 'ps1':
            content = (
                f'<#\n  Description: {desc}\n  Type: {lang_label}\n#>\n'
                '$ErrorActionPreference = "Continue"\n\n'
                'function Run-Script {\n'
                f'    Write-Host "[*] Executing: {desc.replace(chr(34), chr(39))}" -ForegroundColor Cyan\n'
                '    # أضف أوامر التنفيذ هنا\n'
                '}\n\nRun-Script\n'
            )
        elif ext == 'py':
            content = (
                f'"""\nDescription: {desc}\nType: {lang_label}\n"""\n\n'
                'def main():\n'
                f'    print("Running: {desc.replace(chr(34), chr(39))}")\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )
        elif ext == 'js':
            content = (
                f'/* Description: {desc} | Type: {lang_label} */\n'
                'function main() {\n'
                f'  console.log("Running: {desc.replace(chr(34), chr(39))}");\n'
                '}\n\nmain();\n'
            )
        else:
            content = (
                f'#!/usr/bin/env bash\n'
                f'# Description: {desc} | Type: {lang_label}\n'
                'set -euo pipefail\n\n'
                f'echo "Running: {desc.replace(chr(34), chr(39))}"\n'
            )

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)

        Clipboard.copy(content)
        self.speak(f'تم إنشاء السكربت {os.path.basename(out_path)} ونسخه للحافظة وحفظه في {out_path} يا شيخ')

    def generate_ps1_script(self, task_desc):
        safe_name = re.sub(r'[^\w\-]+', '_', task_desc.strip().lower()).strip('_') or 'custom_task'
        safe_name = safe_name[:40]
        out_path = os.path.join(PS1_DIR, f'{safe_name}.ps1')
        escaped_desc = task_desc.replace('"', '`"')

        script_content = (
            '<#\n'
            f'  Task: {task_desc}\n'
            '  Generated by Napoleon Assistant\n'
            '#>\n'
            '$ErrorActionPreference = "Continue"\n\n'
            'function Invoke-NapoleonTask {\n'
            '    param(\n'
            f'        [string]$TaskName = "{escaped_desc}"\n'
            '    )\n'
            '    Write-Host "[+] Starting PS1 Task: $TaskName" -ForegroundColor Cyan\n'
            '    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"\n'
            '    Write-Host "[*] Timestamp: $timestamp" -ForegroundColor Gray\n\n'
            '    # ضع أوامر التنفيذ الخاصة بـ $TaskName هنا:\n'
            '    # مثال: Get-Process | Select-Object -First 10\n'
            '    # مثال: Get-NetTCPConnection -State Established\n'
            '    # مثال: Get-ChildItem -Path . -Recurse\n\n'
            '    Write-Host "[+] Task block ready for: $TaskName" -ForegroundColor Green\n'
            '}\n\n'
            'Invoke-NapoleonTask\n'
        )

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        Clipboard.copy(script_content)
        self.speak(f'تم تجهيز سكربت {safe_name}.ps1 ونسخه للحافظة وحفظه في {out_path} يا شيخ')

    def on_typing_live_check(self, instance, value):
        stripped = value.lstrip()
        if stripped.startswith(('def ', 'class ', 'for ', 'if ', 'while ', 'try:', 'import ', 'from ')):
            try:
                ast.parse(value)
                self.speech_bubble.text = 'الصياغة سليمة حتى الآن'
            except SyntaxError as se:
                self.speech_bubble.text = f'تنبيه أثناء الكتابة (سطر {se.lineno}): {se.msg}'

    def watch_code_file_loop(self, dt):
        target = self.watched_file
        if not target or not os.path.exists(target):
            return
        try:
            with open(target, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return

        h = hash(content)
        if h == self.last_watched_hash:
            return
        self.last_watched_hash = h

        err_msg = self._detect_code_issue(target, content)
        if err_msg:
            sig = f'{target}:{err_msg}'
            if sig != self.last_error_signature:
                self.last_error_signature = sig
                self.speak(f'خطأ في {os.path.basename(target)}: {err_msg}')
        else:
            self.last_error_signature = None

    def _detect_code_issue(self, filepath, content):
        if filepath.endswith('.py'):
            try:
                ast.parse(content)
                return None
            except SyntaxError as se:
                return f'سطر {se.lineno} - {se.msg}'
        if not self._brackets_balanced(content):
            return 'خلل في الأقواس أو علامات التنصيص'
        return None

    def fix_code_any_language(self, filepath_or_code):
        if os.path.exists(filepath_or_code):
            with open(filepath_or_code, 'r', encoding='utf-8') as f:
                raw = f.read()
            fname = os.path.basename(filepath_or_code)
            fixed = self._apply_universal_fixes(raw, is_py=filepath_or_code.endswith('.py'))
            out_path = os.path.join(FIXED_DIR, f'fixed_{fname}')
            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(fixed)
            with open(filepath_or_code, 'w', encoding='utf-8') as orig_f:
                orig_f.write(fixed)
            Clipboard.copy(fixed)
            self.speak(f'تم تصحيح {fname} وتحديثه وحفظ نسخة في {out_path} يا شيخ')
        else:
            fixed = self._apply_universal_fixes(filepath_or_code, is_py=False)
            Clipboard.copy(fixed)
            self.speak('تم تصحيح الكود ونسخه إلى الحافظة يا شيخ')

    def _apply_universal_fixes(self, code, is_py=False):
        lines = code.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        cleaned_lines = []
        for line in lines:
            if is_py:
                leading = re.match(r'^[\t ]*', line).group(0).replace('\t', '    ')
                rest = line.lstrip('\t ').rstrip()
                cleaned_lines.append(leading + rest)
            else:
                cleaned_lines.append(line.rstrip())
        return '\n'.join(cleaned_lines).rstrip() + '\n'

    def _http_translate(self, text, src_lang, dst_lang):
        try:
            q = urllib.parse.quote(text)
            url = f'https://api.mymemory.translated.net/get?q={q}&langpair={src_lang}|{dst_lang}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                translated = data.get('responseData', {}).get('translatedText', '').strip()
                if translated and 'MYMEMORY WARNING' not in translated.upper():
                    return translated
        except Exception:
            pass
        return None

    def translate_ar_to_fr_en(self, text):
        key = text.strip().lower()
        if key in OFFLINE_AR_TO_FR_EN:
            fr_txt, en_txt = OFFLINE_AR_TO_FR_EN[key]
            self._show_and_pronounce_fr_en(text, fr_txt, en_txt)
            return

        self.speak(f'أترجم لك: {text}')

        def worker():
            fr_res = self._http_translate(text, 'ar', 'fr') or 'ترجمة فرنسية غير متاحة حالياً'
            en_res = self._http_translate(text, 'ar', 'en') or 'English translation unavailable'
            Clock.schedule_once(lambda dt: self._show_and_pronounce_fr_en(text, fr_res, en_res), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _show_and_pronounce_fr_en(self, orig, fr_txt, en_txt):
        display = f'{orig}\nFR: {fr_txt}\nEN: {en_txt}'
        self.speech_bubble.text = display
        Clipboard.copy(f'FR: {fr_txt}\nEN: {en_txt}')
        if self.tts and self.tts_ready:
            self.speak(fr_txt, lang_code='fr', queue_mode=TextToSpeech.QUEUE_FLUSH)
            self.speak(en_txt, lang_code='en', queue_mode=TextToSpeech.QUEUE_ADD)
            self.speak('', lang_code='ar', queue_mode=TextToSpeech.QUEUE_ADD)

    def translate_foreign_to_ar(self, text):
        key = text.strip().lower()
        if key in OFFLINE_FOREIGN_TO_AR:
            ar_txt = OFFLINE_FOREIGN_TO_AR[key]
            self.speech_bubble.text = f'{text}\nAR: {ar_txt}'
            Clipboard.copy(ar_txt)
            self.speak(ar_txt, lang_code='ar')
            return

        self.speak(f'أترجم إلى العربية: {text}', lang_code='ar')

        def worker():
            ar_res = self._http_translate(text, 'fr', 'ar')
            if not ar_res or ar_res.lower() == key:
                ar_res = self._http_translate(text, 'en', 'ar')
            ar_final = ar_res or 'تعذر الحصول على الترجمة الآن'
            Clock.schedule_once(lambda dt: self._finish_foreign_to_ar(text, ar_final), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_foreign_to_ar(self, orig, ar_txt):
        self.speech_bubble.text = f'{orig}\nAR: {ar_txt}'
        Clipboard.copy(ar_txt)
        self.speak(ar_txt, lang_code='ar')

    def load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_reminders(self):
        with open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)

    def process_command(self, instance):
        cmd = self.cmd_input.text.strip()
        self.cmd_input.text = ''
        if not cmd:
            return

        if re.match(r'^سكربت\s+', cmd, re.IGNORECASE):
            desc = re.sub(r'^سكربت\s+', '', cmd, flags=re.IGNORECASE).strip()
            self.generate_any_script(desc)
        elif re.match(r'^(?:ps1|باور\s*شيل|باورشيل|سكربت\s*ps1)\s+', cmd, re.IGNORECASE):
            task_desc = re.sub(r'^(?:ps1|باور\s*شيل|باورشيل|سكربت\s*ps1)\s+', '', cmd, flags=re.IGNORECASE).strip()
            self.generate_ps1_script(task_desc)
        elif re.match(r'^(?:راقب|تابع)\s+', cmd):
            target = re.sub(r'^(?:راقب|تابع)\s+', '', cmd).strip()
            self.watched_file = target
            self.last_watched_hash = None
            self.last_error_signature = None
            self.speak(f'أراقب الملف {target} لحظياً يا شيخ')
        elif re.match(r'^(?:صحح|صلح|عدل|نفذ)\s+', cmd):
            target = re.sub(r'^(?:صحح|صلح|عدل|نفذ)\s+', '', cmd).strip()
            self.fix_code_any_language(target)
        elif re.match(r'^ترجم(?:\s+(?:لل?فرنسي|لل?انجليزي|لل?إنجليزي))?\s+', cmd):
            target = re.sub(r'^ترجم(?:\s+(?:لل?فرنسي|لل?انجليزي|لل?إنجليزي))?\s+', '', cmd).strip()
            self.translate_ar_to_fr_en(target)
        elif re.match(r'^(?:عربي|ترجم\s+عربي|للعربي)\s+', cmd):
            target = re.sub(r'^(?:عربي|ترجم\s+عربي|للعربي)\s+', '', cmd).strip()
            self.translate_foreign_to_ar(target)
        elif re.search(r'[a-zA-ZÀ-ÿ]', cmd) and not cmd.startswith(('افتح ', 'كود ', 'فحص ', 'خطأ ', 'حل ', 'شرح ', 'جافا ', 'ps1 ', 'PS1 ', 'سكربت ')):
            self.translate_foreign_to_ar(cmd)
        elif cmd.startswith('افتح '):
            app_name = cmd.replace('افتح ', '', 1).strip().lower()
            self.open_installed_app(app_name)
        elif cmd.startswith('ذكرني') or cmd.startswith('تذكير'):
            self.parse_and_schedule_reminder(cmd)
        elif cmd in ('مواعيدي', 'عرض المواعيد'):
            self.list_reminders()
        elif re.match(r'^جافا\s+apk\b', cmd, re.IGNORECASE):
            files_part = re.sub(r'^جافا\s+apk\s*', '', cmd, flags=re.IGNORECASE).strip()
            self.prepare_java_apk_project(files_part)
        elif cmd.startswith('كود '):
            lang_arg = cmd.replace('كود ', '', 1).strip().lower()
            self.generate_code_template(lang_arg)
        elif cmd.startswith('فحص '):
            file_arg = cmd.replace('فحص ', '', 1).strip()
            self.inspect_code_file(file_arg)
        elif cmd.startswith('خطأ ') or cmd.startswith('حل ') or cmd.startswith('شرح '):
            err_query = re.sub(r'^(خطأ|حل|شرح)\s+', '', cmd).strip()
            self.search_code_error(err_query)
        else:
            self.search_web(cmd)

    def prepare_java_apk_project(self, files_part):
        raw_files = [f.strip() for f in files_part.split() if f.strip()]
        if not raw_files:
            self.speak('اكتب أسماء ملفات الجافا يا شيخ، مثلاً: جافا apk A.java B.java C.java')
            return

        missing = [f for f in raw_files if not os.path.exists(f)]
        if missing:
            self.speak(f'ما لقيت الملفات التالية: {", ".join(missing)}')
            return

        src_java_dir = os.path.join(JAVA_BUILD_DIR, 'app', 'src', 'main', 'java', 'com', 'napoleon', 'app')
        wf_dir = os.path.join(JAVA_BUILD_DIR, '.github', 'workflows')
        if os.path.exists(JAVA_BUILD_DIR):
            shutil.rmtree(JAVA_BUILD_DIR)
        os.makedirs(src_java_dir, exist_ok=True)
        os.makedirs(wf_dir, exist_ok=True)

        has_main_activity = False
        for fpath in raw_files:
            fname = os.path.basename(fpath)
            if fname == 'MainActivity.java':
                has_main_activity = True
            with open(fpath, 'r', encoding='utf-8') as src_f:
                content = src_f.read()
            cleaned = re.sub(r'^\s*package\s+[\w.]+\s*;\s*', '', content, flags=re.MULTILINE)
            with open(os.path.join(src_java_dir, fname), 'w', encoding='utf-8') as dst_f:
                dst_f.write('package com.napoleon.app;\n\n' + cleaned)

        if not has_main_activity:
            main_act_code = (
                'package com.napoleon.app;\n\n'
                'import android.app.Activity;\n'
                'import android.os.Bundle;\n'
                'import android.widget.TextView;\n\n'
                'public class MainActivity extends Activity {\n'
                '    @Override\n'
                '    protected void onCreate(Bundle savedInstanceState) {\n'
                '        super.onCreate(savedInstanceState);\n'
                '        TextView tv = new TextView(this);\n'
                '        tv.setText("Napoleon Java App");\n'
                '        setContentView(tv);\n'
                '    }\n'
                '}\n'
            )
            with open(os.path.join(src_java_dir, 'MainActivity.java'), 'w', encoding='utf-8') as f:
                f.write(main_act_code)

        manifest_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    package="com.napoleon.app">\n'
            '    <application android:label="NapoleonJavaApp">\n'
            '        <activity android:name=".MainActivity" android:exported="true">\n'
            '            <intent-filter>\n'
            '                <action android:name="android.intent.action.MAIN" />\n'
            '                <category android:name="android.intent.category.LAUNCHER" />\n'
            '            </intent-filter>\n'
            '        </activity>\n'
            '    </application>\n'
            '</manifest>\n'
        )
        with open(os.path.join(JAVA_BUILD_DIR, 'app', 'src', 'main', 'AndroidManifest.xml'), 'w', encoding='utf-8') as f:
            f.write(manifest_xml)

        gh_workflow = (
            'name: Build Java APK\n\n'
            'on:\n'
            '  push:\n'
            '    branches: [ main ]\n'
            '  workflow_dispatch:\n\n'
            'jobs:\n'
            '  build:\n'
            '    runs-on: ubuntu-latest\n'
            '    steps:\n'
            '      - uses: actions/checkout@v4\n'
            '      - uses: actions/setup-java@v4\n'
            '        with:\n'
            '          distribution: temurin\n'
            '          java-version: "17"\n'
            '      - uses: android-actions/setup-android@v3\n'
            '      - name: Compile Java & Build APK\n'
            '        run: |\n'
            '          cd java_apk_build\n'
            '          mkdir -p build/classes build/dex build/apk\n'
            '          PLATFORM_JAR=$(find "$ANDROID_HOME/platforms" -name "android.jar" | sort -V | tail -n 1)\n'
            '          javac -source 17 -target 17 -cp "$PLATFORM_JAR" -d build/classes $(find app/src/main/java -name "*.java")\n'
            '          D8=$(find "$ANDROID_HOME/build-tools" -name "d8" | sort -V | tail -n 1)\n'
            '          "$D8" --lib "$PLATFORM_JAR" --output build/dex $(find build/classes -name "*.class")\n'
            '          AAPT2=$(find "$ANDROID_HOME/build-tools" -name "aapt2" | sort -V | tail -n 1)\n'
            '          "$AAPT2" link -o build/unsigned.apk -I "$PLATFORM_JAR" --manifest app/src/main/AndroidManifest.xml --min-sdk-version 24 --target-sdk-version 33\n'
            '          cp build/dex/classes.dex . && zip -j build/unsigned.apk classes.dex\n'
            '          ZIPALIGN=$(find "$ANDROID_HOME/build-tools" -name "zipalign" | sort -V | tail -n 1)\n'
            '          "$ZIPALIGN" -p 4 build/unsigned.apk build/aligned.apk\n'
            '          APKSIGNER=$(find "$ANDROID_HOME/build-tools" -name "apksigner" | sort -V | tail -n 1)\n'
            '          keytool -genkeypair -v -keystore build/debug.keystore -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android -dname "CN=Napoleon,O=Dev,C=SA"\n'
            '          "$APKSIGNER" sign --ks build/debug.keystore --ks-pass pass:android --key-pass pass:android --out build/apk/NapoleonJava.apk build/aligned.apk\n'
            '      - uses: actions/upload-artifact@v4\n'
            '        with:\n'
            '          name: napoleon-java-apk\n'
            '          path: java_apk_build/build/apk/*.apk\n'
        )
        with open(os.path.join(wf_dir, 'build-java-apk.yml'), 'w', encoding='utf-8') as f:
            f.write(gh_workflow)

        self.speak(f'جهزت مشروع الجافا لـ {len(raw_files)} ملفات في {JAVA_BUILD_DIR} يا شيخ')

    def generate_code_template(self, lang_arg):
        canonical = LANG_ALIASES.get(lang_arg)
        if canonical and canonical in LANGUAGES_DB:
            ext, code_text = LANGUAGES_DB[canonical]
            lang_label = canonical
        else:
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', lang_arg) or 'code'
            ext = clean_name[:10]
            lang_label = lang_arg
            code_text = f'// {lang_label} template\n'

        Clipboard.copy(code_text)
        out_path = os.path.join(SNIPPETS_DIR, f'template_{re.sub(r"[^a-zA-Z0-9_-]", "_", lang_label)}.{ext}')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(code_text)

        self.speak(f'جهزت قالب {lang_label} ونسخته للحافظة وحفظته في {out_path}')

    def _brackets_balanced(self, text):
        pairs = {'{': '}', '(': ')', '[': ']'}
        stack = []
        in_str = None
        escape = False
        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if in_str:
                if ch == in_str:
                    in_str = None
                continue
            if ch in ('"', "'", '`'):
                in_str = ch
            elif ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values():
                if not stack or stack.pop() != ch:
                    return False
        return len(stack) == 0 and in_str is None

    def inspect_code_file(self, filepath):
        if not os.path.exists(filepath):
            self.speak(f'ما لقيت الملف {filepath} يا شيخ')
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.speak(f'تعذر قراءة الملف: {e}')
            return

        lines = content.splitlines()
        line_count = len(lines)

        if filepath.endswith('.py'):
            try:
                tree = ast.parse(content)
                funcs = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
                self.speak(f'سليم نحوياً يا شيخ! {line_count} سطر، {classes} كلاس، و {funcs} دالة')
            except SyntaxError as se:
                self.speak(f'فيه خطأ نحوي في السطر {se.lineno}: {se.msg}')
            return

        fn_matches = len(re.findall(
            r'\b(?:def|function|func|fn|sub|procedure|void|int|string|public\s+static|async\s+function)\b',
            content,
        ))
        cls_matches = len(re.findall(r'\b(?:class|struct|interface|enum|trait)\b', content))
        balanced = self._brackets_balanced(content)
        status = 'الأقواس متوازنة' if balanced else 'تنبيه: في خلل في الأقواس أو النصوص'
        self.speak(f'{line_count} سطر، {cls_matches} كلاس، {fn_matches} دالة، و {status} يا شيخ')

    def search_code_error(self, err_query):
        self.speak(f'أفتش لك عن حل في الأكواد: {err_query}')
        q = urllib.parse.quote(f'{err_query} code documentation OR stackoverflow OR github')
        url = f'https://www.google.com/search?q={q}'
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        self.context.startActivity(intent)

    def parse_and_schedule_reminder(self, cmd):
        day_match = re.search(r'يوم\s+(\d{1,2})', cmd)
        month_match = re.search(r'شهر\s+(\d{1,2})', cmd)
        time_match = re.search(r'الساعة\s+(\d{1,2})(?::(\d{1,2}))?', cmd)

        if not (day_match and month_match and time_match):
            self.speak('اكتبها كذا يا شيخ: ذكرني [الموعد] يوم 25 شهر 11 الساعة 18:30')
            return

        day = int(day_match.group(1))
        month = int(month_match.group(2))
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0

        if ('مساء' in cmd or 'م' in cmd.split()) and hour < 12:
            hour += 12
        elif ('صباح' in cmd or 'ص' in cmd.split()) and hour == 12:
            hour = 0

        title_part = cmd[:day_match.start()]
        title = re.sub(r'^(ذكرني|تذكير)\s*', '', title_part).strip()
        if not title:
            title = 'موعد مهم'

        now = datetime.datetime.now()
        year = now.year
        try:
            target_dt = datetime.datetime(year, month, day, hour, minute)
            if target_dt < now:
                target_dt = datetime.datetime(year + 1, month, day, hour, minute)
        except ValueError:
            self.speak('التاريخ أو الوقت غير صحيح يا شيخ!')
            return

        reminder_item = {
            'title': title,
            'timestamp': target_dt.timestamp(),
            'display_time': target_dt.strftime('%Y-%m-%d %H:%M'),
            'notified': False,
        }
        self.reminders.append(reminder_item)
        self.save_reminders()
        self.schedule_android_alarm(target_dt, len(self.reminders))

        self.speak(
            f'تم يا شيخ! سأذكرك بـ {title} يوم {day} شهر {month} الساعة {hour:02d}:{minute:02d}'
        )

    def schedule_android_alarm(self, target_dt, req_code):
        try:
            alarm_mgr = self.context.getSystemService(Context.ALARM_SERVICE)
            intent = Intent(self.context, PythonActivity)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP)
            flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            pending = PendingIntent.getActivity(self.context, req_code, intent, flags)

            cal = Calendar.getInstance()
            cal.set(target_dt.year, target_dt.month - 1, target_dt.day, target_dt.hour, target_dt.minute, 0)
            alarm_mgr.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                cal.getTimeInMillis(),
                pending,
            )
        except Exception:
            pass

    def check_due_reminders(self, dt):
        now_ts = datetime.datetime.now().timestamp()
        updated = False
        for item in self.reminders:
            if not item.get('notified') and now_ts >= item['timestamp']:
                item['notified'] = True
                updated = True
                self.speak(f'تنبيه يا شيخ! حان الآن موعد: {item["title"]}')
        if updated:
            self.save_reminders()

    def list_reminders(self):
        upcoming = [r for r in self.reminders if not r.get('notified')]
        if not upcoming:
            self.speak('لا توجد مواعيد قادمة يا شيخ')
            return
        first = upcoming[0]
        self.speak(f'عندك {len(upcoming)} مواعيد، أقربها: {first["title"]} في {first["display_time"]}')

    def open_installed_app(self, target_name):
        pm = self.context.getPackageManager()
        packages = pm.getInstalledApplications(PackageManager.GET_META_DATA)

        found_package = None
        for i in range(packages.size()):
            app_info = packages.get(i)
            label = str(pm.getApplicationLabel(app_info)).lower()
            if target_name in label:
                found_package = app_info.packageName
                break

        if found_package:
            launch_intent = pm.getLaunchIntentForPackage(found_package)
            if launch_intent:
                self.speak(f'أمرك مطاع يا شيخ، جاري فتح {target_name}')
                self.context.startActivity(launch_intent)
                return

        self.speak(f'لم أجد تطبيقاً باسم {target_name}')

    def search_web(self, query):
        self.speak(f'إلى الأمام يا شيخ، أبحث لك عن: {query}')
        encoded_query = urllib.parse.quote(query)
        url = f'https://www.google.com/search?q={encoded_query}'
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        self.context.startActivity(intent)


class NapoleonApp(App):
    def build(self):
        self.check_overlay_permission()
        Window.clearcolor = (0, 0, 0, 0)
        return NapoleonWidget()

    def check_overlay_permission(self):
        context = PythonActivity.mActivity
        if not Settings.canDrawOverlays(context):
            intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse('package:' + context.getPackageName()),
            )
            context.startActivity(intent)


if __name__ == '__main__':
    NapoleonApp().run()

# BypassManager

> Удобный GUI-менеджер для запуска [zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube) и [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) от [Flowseal](https://github.com/Flowseal).

![Windows](https://img.shields.io/badge/Windows-10%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Что это

BypassManager - графическая оболочка, которая позволяет одной кнопкой включать и выключать:

- **Discord / YouTube** - обход блокировок через zapret (DPI)
- **Telegram** - MTProto-прокси через tg-ws-proxy

Сам по себе не содержит никакого кода обхода - только запускает и останавливает оригинальные инструменты.

---

## Скачать

Готовая сборка - в разделе [Releases](../../releases/latest).

В архиве уже всё необходимое:
```
BypassManager.exe
zapret/         - zapret-discord-youtube от Flowseal
tg_proxy/       - tg-ws-proxy от Flowseal
```

> ⚠️ Антивирус может ругаться на `WinDivert.dll` / `WinDivert64.sys` - это нормально.
> WinDivert является легитимным драйвером для перехвата трафика.
> Подробнее: [README zapret](https://github.com/Flowseal/zapret-discord-youtube#readme)

---

## Сборка из исходников

Если не доверяешь готовому exe - собери сам.

### 1. Установи Python 3.11+

Скачай с [python.org](https://python.org). При установке обязательно поставь галочку **"Add Python to PATH"**.

### 2. Установи зависимости

```
pip install pyinstaller customtkinter pillow pystray pyperclip
```

### 3. Скачай оригинальные инструменты

- [zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube/releases/latest) - распакуй содержимое в папку `zapret/`
- [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy/releases/latest) - распакуй содержимое в папку `tg_proxy/`

### 4. Настрой листы исключений

Открой `zapret/lists/list-exclude-user.txt` и добавь домены которые **не нужно** обходить (например Warframe):
```
warframe.com
content.warframe.com
origin.warframe.com
cdn.warframe.com
forums.warframe.com
```

Открой `zapret/lists/list-general-user.txt` и добавь домены которые **нужно** обходить (добавляются к основному списку):
```

# любые нужные тебе домены
```

### 5. Структура папки перед сборкой

```
bypass/
├── manager.py
├── BypassManager.manifest
├── zapret/
│   ├── bin/
│   │   ├── winws.exe
│   │   ├── WinDivert.dll
│   │   └── WinDivert64.sys
│   ├── lists/
│   │   ├── list-general.txt
│   │   ├── list-general-user.txt   ← твои домены для обхода
│   │   └── list-exclude-user.txt   ← твои исключения
│   └── general.bat
└── tg_proxy/
    └── tgneclocer.exe  ← собранный tg-ws-proxy
```

### 6. Отключи автообновление с сервера (опционально)

По умолчанию приложение проверяет обновления zapret на `neclocer.tech`.
Если хочешь убрать это и использовать только GitHub - найди в `manager.py` строки:

```python
UPDATE_HOST = "https://neclocer.tech/bypass"
```

и в функции `check_zapret_update()` удали блок проверки своего хоста:

```python
# удали этот блок целиком (строки ~163-173):
try:
    req = urllib.request.Request(
        f"{UPDATE_HOST}/zapret_version.txt",
        ...
    )
    ...
    return remote_ver, f"{UPDATE_HOST}/zapret.zip"
except Exception:
    pass
```

Если хочешь убрать автообновление **вообще** - удали кнопку `⟳ Обновить zapret` из UI:
найди и удали строки в `manager.py`:

```python
self._upd_btn = tk.Button(hdr, text="⟳ Обновить zapret", ...)
self._upd_btn.pack(side="right")
```

и вызов проверки при запуске:
```python
self.after(3000, self._check_update_bg)
```

### 7. Собери exe

```
py -m PyInstaller --onefile --windowed --name BypassManager --manifest BypassManager.manifest manager.py
```

Готовый `BypassManager.exe` появится в папке `dist/`.
Скопируй туда папки `zapret/` и `tg_proxy/`.

---

## Использование

1. Запусти `BypassManager.exe` — автоматически запросит права администратора
2. Включи нужные сервисы ползунком
3. Для Discord/YouTube выбери вариант из списка (Стандартный, ALT, FAKE TLS AUTO и т.д.)

---

## Функции

- Включение/выключение zapret одной кнопкой
- Включение/выключение tg-ws-proxy одной кнопкой
- Выбор стратегии обхода (все варианты bat-файлов определяются автоматически)
- Проверка и установка обновлений zapret
- Сохранение выбранного варианта между запусками

---

## Благодарности

Весь код обхода написан не мной:

| Проект | Автор | Лицензия |
|--------|-------|----------|
| [zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube) | [Flowseal](https://github.com/Flowseal) | MIT |
| [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) | [Flowseal](https://github.com/Flowseal) | MIT |
| [zapret](https://github.com/bol-van/zapret) | [bol-van](https://github.com/bol-van) | MIT |
| [WinDivert](https://github.com/basil00/WinDivert) | basil00 | LGPLv3/GPLv2 |

---

## Лицензия

MIT — см. [LICENSE](LICENSE)

Код BypassManager (`manager.py`) написан мной и распространяется под лицензией MIT.
Включённые бинарники zapret и tg-ws-proxy распространяются под лицензиями их авторов (см. выше).

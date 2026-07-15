# Iron Squad — Мобильный шутер

## Быстрый старт

### Играть в браузере
1. Открой `game/index.html` в браузере на телефоне
2. В браузере на ПК: зайди на тот же WiFi, открой `http://<IP>:8080`
3. Запусти локальный сервер: `cd game && python3 -m http.server 8080`

### Собрать APK

**Способ 1: GitHub Actions (рекомендуется)**
1. Запушь код в GitHub
2. Вкладка Actions → Build APK → Run workflow
3. Скачай APK из вкладки Artifacts

**Способ 2: Локальная сборка**
```bash
chmod +x build-apk.sh
./build-apk.sh
```
Требования: JDK 17, Android SDK (скачается автоматически)

**Способ 3: Android Studio**
1. Открой папку `game/android` в Android Studio
2. Build → Build Bundle(s) / APK(s) → Build APK(s)

### Установка на телефон
```bash
adb install iron-squad.apk
```
Или отправь APK файлом на телефон и установи вручную.

## Управление

| Действие | Мобильный | ПК |
|----------|-----------|-----|
| Движение | Левый стик | WASD |
| Прицел + стрельба | Правая часть экрана | Мышь |
| Смена оружия | Кнопки внизу справа | 1-5 |
| Перезарядка | Автоматически | R |
| Пауза | Escape | Escape |

## Режимы
- **В бой** — классические волны PvE с нарастающей сложностью
- **Выживание** — больше HP, без волн, просто выживай

## Структура проекта
```
мобильная игра/
├── game/
│   ├── index.html              ← игра (HTML5 Canvas)
│   ├── build-apk.sh            ← скрипт локальной сборки
│   ├── .github/workflows/      ← CI/CD для GitHub Actions
│   └── android/                ← Android проект (WebView wrapper)
│       ├── app/src/main/
│       │   ├── AndroidManifest.xml
│       │   ├── java/.../MainActivity.java
│       │   ├── assets/index.html
│       │   └── res/
│       ├── build.gradle
│       └── gradlew
├── prompt_mobile_shooter.md    ← исходный промт
├── game_design_overview.md     ← GDD
└── README.md
```

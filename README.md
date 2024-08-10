# Gpon_interface_v1 (Tkinter)
## Один из самых первых моих учебных проектов на Python (2020 год)

### Цель
Преобразовать CLI[ssh] интерфейс в графический, упростить взаимодействие с Gpon-блоком

### Основа
Проект базируется на двух библиотеках:
* Tkinter (desktop gui)
* Paramiko (ssh cmds)

### Взаимодействие
desktop gui -> paramiko -> ssh -> cli -> gpon

### Установка
Установка tkinter
```
sudo apt get install python3-tk
```

Установка окружения, сначала перейти в корень папки проекта
```
python -m venv venv
```

Активация venv для windows
```
venv\Scripts\activate.bat
```
Активация venv для linux
```
source venv\bin\activate
```

Установка необходимых библиотек
```
pip install -r requirements.txt
```

Запуск
```
python main.py
```

# Geração de executável
pyinstaller --onefile --hidden-import=pyshorteners --hidden-import=pyshorteners.shorteners --hidden-import=pyshorteners.shorteners.tinyurl main.py

ou

pyinstaller --onefile ^
  --hidden-import=pyshorteners ^
  --hidden-import=pyshorteners.shorteners ^
  --hidden-import=pyshorteners.shorteners.tinyurl ^
  main.py

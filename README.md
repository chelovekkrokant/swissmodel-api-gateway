# PredictingProteinStructure

Микросервис предсказания трёхмерной структуры белка через SWISS-MODEL API.  
Принимает FASTA-файл (и опционально PDB-шаблон), запускает моделирование и возвращает готовый PDB-файл.

---
## Запуск

1. Скопируй `.env.example` в `.env` и укажи свой API-ключ SWISS-MODEL:

```bash
cp .env.example .env
# отредактируй .env: SWISSMODEL_API_KEY=your_token_here
```

2. Запусти через Docker Compose:

```bash
docker compose up --build
```

Сервис поднимается на порту, указанном в `.env` (по умолчанию `10002`).

---

## Использование

### Режим A — без шаблона (автоматический поиск)

```bash
curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@sequence.fasta" \
  -o result.pdb
```

### Режим B — с пользовательским шаблоном

```bash
curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@sequence.fasta" \
  -F "template=@template.pdb" \
  -o result.pdb
```

---

## Проверка критериев приёмки

Все команды выполняются при запущенном сервисе.  
Флаг `-i` выводит заголовки ответа, `-D -` — заголовки в stdout при сохранении тела в файл.

### 1. Режим без шаблона → PDB-файл

```bash
curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@tests/fixtures/seq_2019.fasta" \
  -o /tmp/result_a.pdb -D -

# Ожидаем 200
```

### 2. Режим с шаблоном → PDB-файл

```bash
curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@tests/fixtures/another.fasta" \
  -F "template=@tests/fixtures/H1 2013.pdb" \
  -o /tmp/result_b.pdb -D -

# Ожидаем 200
```

### 3. Логи с различением режимов

```bash
docker compose logs api | grep -E "Mode [AB]|Submitted|Job status|Returning PDB"

# Ожидаем строки вида:
# INFO     [req=xxxxxxxx] app.swissmodel_client: Mode A (automodel): sequences=1
# INFO     [req=yyyyyyyy] app.swissmodel_client: Mode B (user template): sequences=1
```

### 4. Нет fasta или неверное расширение → 400

```bash
# Без fasta
curl -X POST http://127.0.0.1:10002/predict -i
# Ожидаем 400, {"detail":"fasta file required"}

# Неверное расширение
echo "SOME_TEXT_LIKE_A_FASTA" > /tmp/bad.txt
curl -X POST http://127.0.0.1:10002/predict -F "fasta=@/tmp/bad.txt" -i
# Ожидаем 400, {"detail":"fasta file must have .fasta extension"}
```

### 5. Шаблон с неверным расширением → 400

```bash
echo "not pdb" > /tmp/bad.txt
curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@tests/fixtures/another.fasta" \
  -F "template=@/tmp/bad.txt" -i
# Ожидаем 400, {"detail":"template file must have .pdb extension"}
```

### 6. Нет подходящих шаблонов в авто-режиме → 404

SWISS-MODEL отклоняет последовательности короче 30 остатков с ошибкой 400 ещё до поиска шаблонов.  
Для теста нужна последовательность длиннее 30:

```bash
printf '>synthetic\nWQAAAAAAAANMKSFECIVAANRTEQDWSTKGPLV\n' > /tmp/synthetic.fasta
curl -X POST http://127.0.0.1:10002/predict -F "fasta=@/tmp/synthetic.fasta" -i
# Ожидаем 404, {"detail":"No suitable templates found"}
```

> Примечание: 404 возникает только если SWISS-MODEL вернул статус `FAILED` (нет подходящих шаблонов).  
> Если сервер всё же нашёл шаблон для последовательности — ответ будет 200. В этом случае попробуй другую случайную последовательность.

### 7. Превышение времени ожидания → 504

Временно установи `MAX_WAIT_TIME=1` в `.env`, перезапусти сервис:

```bash
# в .env: MAX_WAIT_TIME=1
docker compose down && docker compose up -d

curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@tests/fixtures/seq_2019.fasta" -i
# → HTTP/1.1 504, {"detail":"Job did not complete in 1s"}

# Верни MAX_WAIT_TIME=3600 и перезапусти
```

### 8. Обработка rate limit

Сервис проактивно не превышает 100 запросов/мин и 2000 запросов/6ч.  
При приближении к лимиту в логах появится:

```
INFO     [req=...] app.swissmodel_client: Rate throttle: sleeping 58.3s (minute=100/100, 6h=.../2000)
```

Если SWISS-MODEL вернёт 429 — сервис повторит запрос с экспоненциальным backoff (до 5 раз).

### 9. Временные файлы удаляются

```bash
# До запроса
docker compose exec api sh -c 'ls /tmp | grep ^tmp | wc -l'

# После запроса (любого исхода)
curl -X POST http://127.0.0.1:10002/predict -F "fasta=@/tmp/bad.txt" -i
docker compose exec api sh -c 'ls /tmp | grep ^tmp | wc -l'

# Счётчик должен вернуться к исходному значению
```

### 10. Битый PDB-шаблон → 500

```bash
echo "this is not a pdb" > /tmp/broken.pdb
printf '>seq\nMVLSPADKTNVKAAAAAAAAAAAAAAAAAAAAAAAAAW\n' > /tmp/short.fasta

curl -X POST http://127.0.0.1:10002/predict \
  -F "fasta=@/tmp/short.fasta" \
  -F "template=@/tmp/broken.pdb" -i
# Ожидаем 500, {"detail":"Submission failed: ..."}
```
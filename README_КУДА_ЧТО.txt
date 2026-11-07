ВИДИМЫЕ ФАЙЛЫ — чтобы Windows показывал

1. env.local.txt -> переименуй в .env.local (правый клик -> Переименовать)
2. env.prod.example.txt -> переименуй в .env.prod.example
3. Остальное уже на месте — docker-compose.yml + sticker_print_ui.html + db/init/01_schema.sql

Или включи: Вид -> Показать -> Скрытые элементы

После:
cd C:\Perm_Repair
docker-compose --env-file .env.local up -d --build
Открой sticker_print_ui.html двойным кликом

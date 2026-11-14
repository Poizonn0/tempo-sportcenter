INSERT OR IGNORE INTO users (id, name, email, password_hash, role, phone)
VALUES (1, 'Администратор', 'admin@sportcenter.local', 'scrypt:32768:8:1$vubquXQmcwBbIkv2$3ee9e0fcc75c37194534e8f1e7c1e0969e11bbb6960fda409f311d4efa9ba11613ae12bd12b9fdd68aea8df8ac807f3de2f9546c54fc32b5e31137807ebbf66a', 'admin', '');

INSERT INTO classes (title, category, description, coach, starts_at, duration, capacity, room)
VALUES
('Йога: баланс и дыхание', 'Йога', 'Мягкая практика для гибкости, осанки и спокойствия.', 'Алия Садыкова', strftime('%Y-%m-%dT09:00:00', 'now', '+1 day'), 60, 14, 'Зал Mind'),
('Силовая: full body', 'Фитнес', 'Силовая тренировка на всё тело для любого уровня.', 'Данияр Ахметов', strftime('%Y-%m-%dT11:00:00', 'now', '+1 day'), 55, 12, 'Зал Energy'),
('Бокс: техника', 'Бокс', 'Работа над стойкой, движением и базовыми комбинациями.', 'Тимур Касенов', strftime('%Y-%m-%dT14:00:00', 'now', '+1 day'), 60, 10, 'Зал Fight'),
('Пилатес: здоровая спина', 'Пилатес', 'Контроль движения и укрепление мышц корпуса.', 'Алия Садыкова', strftime('%Y-%m-%dT17:00:00', 'now', '+1 day'), 50, 14, 'Зал Mind'),
('Функциональная тренировка', 'Кроссфит', 'Интервальная работа над силой и выносливостью.', 'Данияр Ахметов', strftime('%Y-%m-%dT19:00:00', 'now', '+1 day'), 60, 12, 'Зал Energy'),
('Открытая тренировка', 'Фитнес', 'Знакомство с программой и тренером.', 'Данияр Ахметов', strftime('%Y-%m-%dT10:00:00', 'now', '+2 day'), 45, 16, 'Зал Energy');

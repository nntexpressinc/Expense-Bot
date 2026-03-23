-- ============================================
-- Expenses Bot - Database Schema
-- PostgreSQL 14+
-- ============================================

-- Удаление существующих таблиц (для чистой установки)
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS transfer_expenses CASCADE;
DROP TABLE IF EXISTS transfers CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS balances CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS transaction_type CASCADE;
DROP TYPE IF EXISTS transfer_status CASCADE;
DROP TYPE IF EXISTS category_type CASCADE;
DROP TYPE IF EXISTS notification_type CASCADE;
DROP TYPE IF EXISTS report_type CASCADE;
DROP TYPE IF EXISTS report_format CASCADE;

-- ============================================
-- ENUM Types
-- ============================================

CREATE TYPE transaction_type AS ENUM (
    'income',           -- Доход
    'expense',          -- Расход
    'transfer_out',     -- Исходящий перевод
    'transfer_in'       -- Входящий перевод
);

CREATE TYPE transfer_status AS ENUM (
    'pending',          -- Ожидает подтверждения
    'completed',        -- Завершён
    'cancelled'         -- Отменён
);

CREATE TYPE category_type AS ENUM (
    'income',           -- Категория доходов
    'expense'           -- Категория расходов
);

CREATE TYPE notification_type AS ENUM (
    'daily_reminder',       -- Ежедневное напоминание
    'transfer_received',    -- Получен перевод
    'transfer_spent',       -- Потрачены средства из перевода
    'budget_warning'        -- Предупреждение о превышении бюджета
);

CREATE TYPE report_type AS ENUM (
    'daily',
    'weekly',
    'monthly',
    'custom'
);

CREATE TYPE report_format AS ENUM (
    'pdf',
    'excel'
);

-- ============================================
-- Таблица: users
-- Пользователи бота
-- ============================================

CREATE TABLE users (
    id BIGINT PRIMARY KEY,                      -- Telegram User ID
    username VARCHAR(255),                      -- Telegram username (без @)
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    default_currency VARCHAR(3) DEFAULT 'RUB',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для users
CREATE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL;
CREATE INDEX idx_users_active ON users(is_active, created_at DESC);

-- ============================================
-- Таблица: categories
-- Категории доходов и расходов
-- ============================================

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type category_type NOT NULL,
    icon VARCHAR(10),                           -- Emoji (🍔, 🚕, 💰)
    is_system BOOLEAN DEFAULT FALSE,            -- Системная категория (не может быть удалена)
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,  -- NULL = системная, иначе пользовательская
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_system_category UNIQUE(name, type, user_id)
);

-- Индексы для categories
CREATE INDEX idx_categories_type ON categories(type);
CREATE INDEX idx_categories_user ON categories(user_id) WHERE user_id IS NOT NULL;

-- ============================================
-- Таблица: transactions
-- Все финансовые операции
-- ============================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type transaction_type NOT NULL,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    description TEXT,
    attachment_file_id VARCHAR(512),
    attachment_type VARCHAR(20),
    attachment_name VARCHAR(255),
    transfer_id UUID,                           -- Связь с таблицей transfers (заполняется позже)
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Валидация: amount должен быть положительным
    CONSTRAINT positive_amount CHECK (amount > 0)
);

-- Индексы для transactions
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date DESC);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_transfer ON transactions(transfer_id) WHERE transfer_id IS NOT NULL;
CREATE INDEX idx_transactions_created ON transactions(created_at DESC);

-- ============================================
-- Таблица: transfers
-- Переводы между пользователями
-- ============================================

CREATE TABLE transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    description TEXT,
    status transfer_status NOT NULL DEFAULT 'pending',
    remaining_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- Ограничения
    CONSTRAINT no_self_transfer CHECK (sender_id != recipient_id),
    CONSTRAINT remaining_amount_valid CHECK (remaining_amount >= 0 AND remaining_amount <= amount)
);

-- Индексы для transfers
CREATE INDEX idx_transfers_sender ON transfers(sender_id, created_at DESC);
CREATE INDEX idx_transfers_recipient ON transfers(recipient_id, created_at DESC);
CREATE INDEX idx_transfers_status ON transfers(status);
CREATE INDEX idx_transfers_sender_status ON transfers(sender_id, status, created_at DESC);
CREATE INDEX idx_transfers_recipient_status ON transfers(recipient_id, status, created_at DESC);

-- Добавляем внешний ключ для transactions.transfer_id
ALTER TABLE transactions 
ADD CONSTRAINT fk_transactions_transfer 
FOREIGN KEY (transfer_id) REFERENCES transfers(id) ON DELETE SET NULL;

-- ============================================
-- Таблица: transfer_expenses
-- Детализация расходов из переводов
-- ============================================

CREATE TABLE transfer_expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id UUID NOT NULL REFERENCES transfers(id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    description TEXT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Один transaction может быть связан только с одним transfer
    CONSTRAINT unique_transaction UNIQUE(transaction_id)
);

-- Индексы для transfer_expenses
CREATE INDEX idx_transfer_expenses_transfer ON transfer_expenses(transfer_id, created_at DESC);
CREATE INDEX idx_transfer_expenses_transaction ON transfer_expenses(transaction_id);

-- ============================================
-- Таблица: balances
-- Текущие балансы пользователей (материализованная view)
-- ============================================

CREATE TABLE balances (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    total_balance DECIMAL(15,2) NOT NULL DEFAULT 0,
    own_balance DECIMAL(15,2) NOT NULL DEFAULT 0,         -- Собственные средства
    received_balance DECIMAL(15,2) NOT NULL DEFAULT 0,    -- Полученные переводы
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для balances
CREATE INDEX idx_balances_updated ON balances(updated_at DESC);

-- ============================================
-- Таблица: notifications
-- Настройки уведомлений пользователей
-- ============================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    time TIME,                                  -- Для daily_reminder
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Уникальная комбинация пользователя и типа уведомления
    CONSTRAINT unique_user_notification UNIQUE(user_id, type)
);

-- Индексы для notifications
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_enabled ON notifications(enabled, type);

-- ============================================
-- Таблица: reports
-- История сгенерированных отчётов
-- ============================================

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type report_type NOT NULL,
    format report_format NOT NULL,
    file_path VARCHAR(500),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Проверка периода
    CONSTRAINT valid_period CHECK (period_end >= period_start)
);

-- Индексы для reports
CREATE INDEX idx_reports_user ON reports(user_id, created_at DESC);
CREATE INDEX idx_reports_period ON reports(period_start, period_end);

-- ============================================
-- Функции для автоматического обновления балансов
-- ============================================

-- Функция для пересчёта баланса пользователя
CREATE OR REPLACE FUNCTION recalculate_balance(p_user_id BIGINT, p_currency VARCHAR(3))
RETURNS VOID AS $$
DECLARE
    v_total_income DECIMAL(15,2);
    v_total_expense DECIMAL(15,2);
    v_received_transfers DECIMAL(15,2);
    v_spent_from_transfers DECIMAL(15,2);
BEGIN
    -- Считаем доходы
    SELECT COALESCE(SUM(amount), 0) INTO v_total_income
    FROM transactions
    WHERE user_id = p_user_id 
      AND type = 'income' 
      AND currency = p_currency;
    
    -- Считаем расходы (не из переводов)
    SELECT COALESCE(SUM(amount), 0) INTO v_total_expense
    FROM transactions t
    WHERE t.user_id = p_user_id 
      AND t.type = 'expense'
      AND t.currency = p_currency
      AND t.id NOT IN (SELECT transaction_id FROM transfer_expenses);
    
    -- Считаем полученные переводы
    SELECT COALESCE(SUM(remaining_amount), 0) INTO v_received_transfers
    FROM transfers
    WHERE recipient_id = p_user_id
      AND status = 'completed'
      AND currency = p_currency;
    
    -- Обновляем или вставляем баланс
    INSERT INTO balances (user_id, currency, total_balance, own_balance, received_balance, updated_at)
    VALUES (
        p_user_id,
        p_currency,
        (v_total_income - v_total_expense + v_received_transfers),
        (v_total_income - v_total_expense),
        v_received_transfers,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (user_id) DO UPDATE SET
        currency = p_currency,
        total_balance = (v_total_income - v_total_expense + v_received_transfers),
        own_balance = (v_total_income - v_total_expense),
        received_balance = v_received_transfers,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Триггеры для автоматического обновления
-- ============================================

-- Обновление updated_at при изменении записи
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Вставка системных категорий
-- ============================================

-- Категории расходов
INSERT INTO categories (name, type, icon, is_system) VALUES
    ('Еда и продукты', 'expense', '🍔', TRUE),
    ('Транспорт', 'expense', '🚕', TRUE),
    ('Жильё', 'expense', '🏠', TRUE),
    ('Коммунальные услуги', 'expense', '💡', TRUE),
    ('Здоровье', 'expense', '💊', TRUE),
    ('Развлечения', 'expense', '🎬', TRUE),
    ('Одежда', 'expense', '👕', TRUE),
    ('Образование', 'expense', '📚', TRUE),
    ('Связь', 'expense', '📱', TRUE),
    ('Подарки', 'expense', '🎁', TRUE),
    ('Спорт', 'expense', '⚽', TRUE),
    ('Красота', 'expense', '💄', TRUE),
    ('Путешествия', 'expense', '✈️', TRUE),
    ('Кафе и рестораны', 'expense', '☕', TRUE),
    ('Разное', 'expense', '📦', TRUE);

-- Категории доходов
INSERT INTO categories (name, type, icon, is_system) VALUES
    ('Зарплата', 'income', '💰', TRUE),
    ('Фриланс', 'income', '💻', TRUE),
    ('Бизнес', 'income', '💼', TRUE),
    ('Инвестиции', 'income', '📈', TRUE),
    ('Подарки', 'income', '🎁', TRUE),
    ('Возврат долга', 'income', '🔙', TRUE),
    ('Разное', 'income', '💵', TRUE);

-- ============================================
-- Представления (Views) для удобных запросов
-- ============================================

-- View: Статистика расходов по категориям за период
CREATE OR REPLACE VIEW v_expenses_by_category AS
SELECT 
    t.user_id,
    c.name AS category_name,
    c.icon AS category_icon,
    COUNT(t.id) AS transaction_count,
    SUM(t.amount) AS total_amount,
    t.currency,
    DATE_TRUNC('month', t.transaction_date) AS month
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE t.type = 'expense'
GROUP BY t.user_id, c.name, c.icon, t.currency, DATE_TRUNC('month', t.transaction_date);

-- View: Детали переводов с информацией о пользователях
CREATE OR REPLACE VIEW v_transfer_details AS
SELECT 
    t.id,
    t.amount,
    t.currency,
    t.description,
    t.status,
    t.remaining_amount,
    t.created_at,
    t.completed_at,
    s.id AS sender_id,
    s.username AS sender_username,
    s.first_name AS sender_first_name,
    r.id AS recipient_id,
    r.username AS recipient_username,
    r.first_name AS recipient_first_name,
    (t.amount - t.remaining_amount) AS spent_amount,
    ROUND((t.amount - t.remaining_amount) / t.amount * 100, 2) AS spent_percentage
FROM transfers t
JOIN users s ON t.sender_id = s.id
JOIN users r ON t.recipient_id = r.id;

-- View: История расходов из переводов
CREATE OR REPLACE VIEW v_transfer_expense_history AS
SELECT 
    te.id,
    te.transfer_id,
    te.amount,
    te.description,
    te.created_at,
    c.name AS category_name,
    c.icon AS category_icon,
    t.transaction_date,
    tr.sender_id,
    tr.recipient_id
FROM transfer_expenses te
JOIN transactions t ON te.transaction_id = t.id
LEFT JOIN categories c ON te.category_id = c.id
JOIN transfers tr ON te.transfer_id = tr.id;

-- ============================================
-- Комментарии к таблицам
-- ============================================

COMMENT ON TABLE users IS 'Пользователи Telegram-бота';
COMMENT ON TABLE categories IS 'Категории доходов и расходов (системные и пользовательские)';
COMMENT ON TABLE transactions IS 'Все финансовые операции (доходы, расходы, переводы)';
COMMENT ON TABLE transfers IS 'Переводы средств между пользователями';
COMMENT ON TABLE transfer_expenses IS 'Детализация расходов из полученных переводов';
COMMENT ON TABLE balances IS 'Текущие балансы пользователей';
COMMENT ON TABLE notifications IS 'Настройки уведомлений пользователей';
COMMENT ON TABLE reports IS 'История сгенерированных отчётов';

-- ============================================
-- Права доступа (для production)
-- ============================================

-- Создание пользователя для приложения (раскомментировать при необходимости)
-- CREATE USER expenses_bot_user WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE expenses_bot TO expenses_bot_user;
-- GRANT USAGE ON SCHEMA public TO expenses_bot_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO expenses_bot_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO expenses_bot_user;

-- ============================================
-- Тестовые данные (для разработки)
-- ============================================

-- Раскомментируйте для создания тестовых данных

/*
-- Тестовые пользователи
INSERT INTO users (id, username, first_name, last_name) VALUES
    (123456789, 'alice', 'Alice', 'Smith'),
    (987654321, 'bob', 'Bob', 'Johnson');

-- Создание начальных балансов
INSERT INTO balances (user_id, currency, total_balance, own_balance, received_balance) VALUES
    (123456789, 'RUB', 10000.00, 10000.00, 0.00),
    (987654321, 'RUB', 5000.00, 5000.00, 0.00);

-- Тестовые транзакции
INSERT INTO transactions (user_id, type, amount, currency, category_id, description) VALUES
    (123456789, 'income', 50000.00, 'RUB', (SELECT id FROM categories WHERE name = 'Зарплата' LIMIT 1), 'Зарплата за январь'),
    (123456789, 'expense', 15000.00, 'RUB', (SELECT id FROM categories WHERE name = 'Еда и продукты' LIMIT 1), 'Продукты за месяц'),
    (987654321, 'income', 30000.00, 'RUB', (SELECT id FROM categories WHERE name = 'Фриланс' LIMIT 1), 'Проект для клиента');

-- Тестовый перевод
INSERT INTO transfers (id, sender_id, recipient_id, amount, currency, description, status, remaining_amount, completed_at)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440000', 123456789, 987654321, 3000.00, 'RUB', 'На продукты', 'completed', 3000.00, CURRENT_TIMESTAMP);

-- Настройки уведомлений по умолчанию
INSERT INTO notifications (user_id, type, enabled, time) VALUES
    (123456789, 'daily_reminder', TRUE, '20:00:00'),
    (123456789, 'transfer_received', TRUE, NULL),
    (123456789, 'transfer_spent', TRUE, NULL),
    (987654321, 'daily_reminder', TRUE, '21:00:00'),
    (987654321, 'transfer_received', TRUE, NULL);
*/

-- ============================================
-- Завершение
-- ============================================

-- Анализ таблиц для оптимизации
ANALYZE users;
ANALYZE categories;
ANALYZE transactions;
ANALYZE transfers;
ANALYZE transfer_expenses;
ANALYZE balances;
ANALYZE notifications;
ANALYZE reports;

SELECT 'Database schema created successfully!' AS status;

import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import HTTPException
from config.settings import settings


def verify_telegram_data(init_data: str) -> dict:
    """
    Проверяет подпись данных от Telegram WebApp
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Парсим данные
        parsed_data = dict(parse_qsl(init_data))
        
        # Извлекаем hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            raise HTTPException(status_code=401, detail="Missing hash in init data")
        
        # Сортируем остальные параметры
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(parsed_data.items())
        )
        
        # Создаём секретный ключ из токена бота
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Проверяем hash
        if not hmac.compare_digest(received_hash, calculated_hash):
            raise HTTPException(status_code=401, detail="Invalid hash")
        
        return parsed_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Telegram data: {str(e)}")

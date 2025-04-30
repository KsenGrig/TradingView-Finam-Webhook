import json
import logging
import re
import os
import yaml
from pathlib import Path
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Только вывод в консоль
    ]
)
logger = logging.getLogger('FinamWebhook')

# Загрузка конфига
def load_config():
    try:
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.critical(f"Config load error: {str(e)}")
        raise

CONFIG = load_config()

class OrderManager:
    def __init__(self):
        self.slippage = CONFIG['risk_management']['slippage']
        self.max_quantity = CONFIG['risk_management']['max_quantity']
        self.allowed_actions = CONFIG['tradingview']['allowed_actions']
        
    def apply_slippage(self, price, action):
        """Применяет проскальзывание к цене с валидацией"""
        try:
            price = float(price)
            if action.lower() == 'buy':
                return round(price + self.slippage, 2)
            elif action.lower() == 'sell':
                return round(price - self.slippage, 2)
            return price
        except Exception as e:
            logger.error(f"Slippage error: {str(e)}")
            return price

    def validate_ticker(self, ticker):
        """Проверяет формат тикера FUT.XXX"""
        return re.match(r'^FUT\.\w{2,5}$', ticker) is not None

    def validate_quantity(self, quantity):
        """Проверяет количество контрактов"""
        try:
            qty = int(quantity)
            return 0 < qty <= self.max_quantity
        except ValueError:
            return False

    def handle_order(self, action, ticker, price, quantity):
        """Отправка ордера с валидацией"""
        if not self.validate_ticker(ticker):
            return False, "Invalid ticker format"
            
        if not self.validate_quantity(quantity):
            return False, f"Quantity must be 1-{self.max_quantity}"
            
        if action.lower() not in self.allowed_actions:
            return False, f"Action must be {', '.join(self.allowed_actions)}"

        try:
            adjusted_price = self.apply_slippage(price, action)
            logger.info(f"Adjusted price: {price} -> {adjusted_price}")
            
            ticker_code = ticker.split('.')[1]
            headers = {
                "X-Api-Key": CONFIG['finam']['token'],
                "Content-Type": "application/json"
            }
            
            payload = {
                "clientId": CONFIG['finam']['client_id'],
                "securityBoard": "FUT",
                "securityCode": ticker_code,
                "buySell": action.capitalize(),
                "quantity": int(quantity),
                "price": float(adjusted_price),
                "property": "PutInQueue"
            }
            
            logger.debug(f"Order payload: {payload}")
            response = requests.post(
                CONFIG['finam']['api_url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API Error: {str(e)}")
            return False, f"API Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return False, f"Internal error: {str(e)}"

def extract_json(raw_data):
    """Извлекает JSON из разных форматов"""
    if isinstance(raw_data, dict):
        return raw_data
        
    try:
        return json.loads(raw_data)
    except json.JSONDecodeError:
        pass
        
    try:
        match = re.search(r'\{[\s\S]*\}', raw_data)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
        
    return None

def handler(event, context):
    order_manager = OrderManager()
    
    try:
        logger.info(f"Incoming event: {event.get('body', '')[:200]}...")
        
        # Валидация IP (если требуется)
        # if event.get('source_ip') not in ALLOWED_IPS...
        
        data = extract_json(event.get('body', ''))
        if not data:
            logger.error("Invalid JSON format")
            return {"statusCode": 400, "body": "Invalid data format"}
            
        logger.debug(f"Parsed data: {json.dumps(data, indent=2)}")
        
        # Проверка парольной фразы
        if data.get('passphrase') != CONFIG['tradingview']['passphrase']:
            logger.warning("Invalid passphrase attempt")
            return {"statusCode": 403, "body": "Forbidden"}
            
        # Извлечение параметров
        strategy = data.get('strategy', {})
        required = {
            'ticker': data.get('ticker'),
            'action': strategy.get('order_action'),
            'price': strategy.get('order_price'),
            'quantity': strategy.get('order_contracts') or strategy.get('order_countracts')
        }
        
        if None in required.values():
            missing = [k for k, v in required.items() if v is None]
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing fields", "missing": missing})
            }
            
        # Исполнение ордера
        success, result = order_manager.handle_order(
            required['action'],
            required['ticker'],
            required['price'],
            required['quantity']
        )
        
        return {
            "statusCode": 200 if success else 500,
            "body": json.dumps({
                "status": "success" if success else "error",
                "message": result if isinstance(result, str) else "Order executed",
                "details": result if not isinstance(result, str) else None
            })
        }
        
    except Exception as e:
        logger.critical(f"Handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

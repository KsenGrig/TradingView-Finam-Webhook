# TradingView-Finam-Webhook
Автоматическое исполнение сделок из TradingView через Finam API
Этот проект позволяет автоматизировать торговлю на брокерской платформе Finam с использованием алертов с сайта TradingView. Стратегия на TradingView генерирует алерты, которые затем отправляются через вебхуки на сервер в Яндекс.Облаке, который, в свою очередь, обрабатывает их и отправляет ордера на платформу Finam.

## Как запустить

1. Разверните функцию в Яндекс.Облаке 
2. Настройте алерты в TradingView , указывая ссылку на ваш вебхук (нужен платный аккаунт).
3. Запустите `index.py` и убедитесь, что он обрабатывает входящие алерты.

## Структура проекта
/function 
├── index.py # Главный файл с функцией
├── requirements.txt # Содержит список зависимостей

## Формат алерта на Trading View
{
  "passphrase": "your_passphrase",
  "ticker": "FUT.your_ticker(например,NGK5)", 
  "strategy": {
    "order_action": "{{strategy.order.action}}",
    "order_contracts": {{strategy.order.contracts}},
    "order_price": {{strategy.order.price}}
  }
}

## Партнерские ссылки для регистрации:
TradingView  - https://ru.tradingview.com/pricing/?share_your_love=kseniagrigoro
Finam - https://www.finam.ru/landings/open-order-new?AgencyBackOfficeID=110&agent=1bc68327-f124-494e-b510-6f27f6b3ce6d&utm_source=cabinet&utm_campaign=friends_program
